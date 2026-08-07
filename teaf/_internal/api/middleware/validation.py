"""``RequestValidationMiddleware`` — valida forma de la petición y tamaño de la respuesta.

La validación de la petición ocurre antes de ``call_next``, que es su razón
de ser: rechazar por ``Content-Length`` cuesta microsegundos y no reserva
memoria, mientras que dejar pasar un cuerpo enorme hasta Pydantic consume
tiempo y RAM que decide el cliente.

La validación de la respuesta ocurre después y solo si hay un límite
efectivo configurado: obliga a materializar el cuerpo (ver
``read_response_body``), y no tiene sentido pagar ese coste cuando el
límite por defecto no va a alcanzarse nunca.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from teaf._internal.api.exceptions import ApiProtectionException, ResponseTooLargeException
from teaf._internal.api.middleware.base import (
    ApiProtectionMiddleware,
    read_response_body,
    rebuild_response,
)
from teaf._internal.api.validation.validator import RequestValidator
from teaf._internal.middleware.exception_handler import build_problem_response


class RequestValidationMiddleware(ApiProtectionMiddleware):
    """Rechaza peticiones malformadas (413/415/400) y respuestas desbordadas (500)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        validator: RequestValidator,
        validate_responses: bool = False,
        **base_options: Any,
    ) -> None:
        """``validate_responses`` está desactivado por defecto: activarlo
        obliga a materializar el cuerpo de toda respuesta, y solo compensa
        cuando existe un límite real que hacer cumplir.

        ``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._validator = validator
        self._validate_responses = validate_responses

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            self._validator.validate_request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
            )
        except ApiProtectionException as exc:
            return self.reject(request, exc)

        response = await call_next(request)

        if not self._validate_responses:
            return response

        body = await read_response_body(response)
        try:
            self._validator.validate_response(content_length=len(body))
        except ResponseTooLargeException as exc:
            self.publish(
                "request.rejected",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "reason": exc.error_code,
                    "responseBytes": len(body),
                },
            )
            return build_problem_response(exc, instance_path=request.url.path)
        return rebuild_response(response, body)
