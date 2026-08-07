"""Manejo centralizado de excepciones.

Traduce la jerarquía de ``backend/core/exceptions.py`` (y cualquier error no
controlado) al formato RFC 7807 exigido por docs/standards/API-STANDARD.md,
sección 6. Es el único lugar del framework que construye una respuesta de
error — ninguna otra capa formatea errores por su cuenta.
"""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from teaf._internal.core.context import get_correlation_id
from teaf._internal.core.exceptions import (
    ApplicationException,
    AuthenticationException,
    AuthorizationException,
    BusinessException,
    ValidationException,
)
from teaf._internal.core.logging import get_logger

_logger = get_logger("teaf.errors")

#: Prefijo de los identificadores "type" de cada problema (ver API-STANDARD.md).
_PROBLEM_BASE_URI = "https://teaf.torus/errors"

#: Código HTTP asociado a cada categoría de excepción de negocio. Se resuelve
#: por el tipo más específico primero; ApplicationException es el fallback.
_STATUS_BY_EXCEPTION_TYPE: dict[type[ApplicationException], int] = {
    ValidationException: status.HTTP_422_UNPROCESSABLE_ENTITY,
    BusinessException: status.HTTP_409_CONFLICT,
    AuthenticationException: status.HTTP_401_UNAUTHORIZED,
    AuthorizationException: status.HTTP_403_FORBIDDEN,
    ApplicationException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _resolve_http_status(exc: ApplicationException) -> int:
    """Código HTTP de ``exc``: el declarado por la excepción, si lo hay; si no, por categoría.

    ``ApplicationException.http_status`` (``None`` salvo que una subclase lo
    fije) tiene prioridad para que una jerarquía definida fuera de ``core/``
    pueda usar códigos que este archivo no conoce — p. ej. 429/413/415/409 de
    ``teaf/_internal/api/exceptions.py`` (Sprint 2.9) — sin que ``middleware/``
    tenga que importar ese subsistema ni ningún otro.
    """
    if exc.http_status is not None:
        return exc.http_status
    for exception_type, http_status in _STATUS_BY_EXCEPTION_TYPE.items():
        if isinstance(exc, exception_type):
            return http_status
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _build_problem_detail(
    *, error_code: str, title: str, http_status: int, detail: str, instance_path: str
) -> dict[str, object]:
    return {
        "type": f"{_PROBLEM_BASE_URI}/{error_code}",
        "title": title,
        "status": http_status,
        "detail": detail,
        "instance": instance_path,
        "correlationId": get_correlation_id(),
    }


def build_problem_response(
    exc: ApplicationException,
    *,
    instance_path: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Construye la respuesta RFC 7807 de ``exc``, fuera del ciclo de manejadores de FastAPI.

    Necesario para los middlewares que rechazan una petición **antes** de
    llamar a ``call_next``: en Starlette, ``ExceptionMiddleware`` (donde
    viven los manejadores registrados con ``app.add_exception_handler``) es
    más *interno* que cualquier middleware de usuario, así que una excepción
    lanzada en el ``dispatch`` de uno de ellos nunca los alcanza. Los
    middlewares de ``teaf/_internal/api/middleware/`` (Sprint 2.9) usan esta
    función para emitir exactamente el mismo formato de error que emitiría
    el manejador centralizado, en vez de inventarse un cuerpo propio.

    ``headers`` añade cabeceras específicas del rechazo (``Retry-After``,
    ``X-RateLimit-*``) sin que esta función necesite conocerlas.
    """
    http_status = _resolve_http_status(exc)
    problem = _build_problem_detail(
        error_code=exc.error_code,
        title=exc.__class__.__name__,
        http_status=http_status,
        detail=exc.message,
        instance_path=instance_path,
    )
    return JSONResponse(status_code=http_status, content=problem, headers=dict(headers or {}))


async def _handle_application_exception(
    request: Request, exc: ApplicationException
) -> JSONResponse:
    http_status = _resolve_http_status(exc)
    if http_status >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        _logger.error("unhandled_application_exception", exc_info=exc)
    problem = _build_problem_detail(
        error_code=exc.error_code,
        title=exc.__class__.__name__,
        http_status=http_status,
        detail=exc.message,
        instance_path=request.url.path,
    )
    return JSONResponse(status_code=http_status, content=problem)


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    problem = _build_problem_detail(
        error_code="validation-error",
        title="ValidationError",
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="El payload de la petición no cumple el contrato esperado.",
        instance_path=request.url.path,
    )
    problem["errors"] = exc.errors()
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=problem)


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Cubre los HTTPException que Starlette/FastAPI lanzan internamente
    (404 de ruta no encontrada, 405 de método no permitido, etc.), que de
    otro modo no pasarían por ``_handle_application_exception`` — sin este
    handler, esas respuestas quedarían fuera del formato RFC 7807 exigido
    por docs/standards/API-STANDARD.md, sección 6.
    """
    problem = _build_problem_detail(
        error_code=f"http-{exc.status_code}",
        title=str(exc.detail),
        http_status=exc.status_code,
        detail=str(exc.detail),
        instance_path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=problem)


async def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    _logger.error("unhandled_exception", exc_info=exc)
    problem = _build_problem_detail(
        error_code="internal-server-error",
        title="InternalServerError",
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        # Nunca se expone el detalle técnico del error al cliente (ver
        # docs/standards/SECURITY-STANDARD.md) — el detalle completo queda
        # en el log correlacionado por correlationId.
        detail="Ocurrió un error interno inesperado.",
        instance_path=request.url.path,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=problem)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores de excepciones centralizados en la aplicación."""
    # Los stubs de Starlette tipan el segundo argumento como Callable[[Request,
    # Exception], ...] de forma invariante, por lo que no aceptan un handler
    # con una excepción más específica aunque sea seguro en tiempo de
    # ejecución (FastAPI despacha por tipo exacto). Limitación conocida del
    # tipado de Starlette/FastAPI, no un error real — se documenta en vez de
    # debilitar la firma de los handlers.
    app.add_exception_handler(ApplicationException, _handle_application_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unhandled_exception)
