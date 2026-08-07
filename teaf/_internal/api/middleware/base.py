"""Base común de los middlewares de protección de APIs (Sprint 2.9, ADR-009).

Concentra las tres cosas que los ocho middlewares necesitan por igual:
construir el ``ApiRequestContext``, publicar eventos en el ``EventBus`` y
emitir un rechazo con el mismo formato RFC 7807 que el resto del framework.

Sobre el rechazo, que es lo menos evidente: un middleware que lanza una
excepción **antes** de ``call_next`` nunca llega a los manejadores
registrados con ``app.add_exception_handler``, porque en Starlette esos
manejadores viven en un middleware más interno que cualquiera de usuario.
Por eso ``reject()`` construye la respuesta directamente, reutilizando
``build_problem_response`` (``middleware/exception_handler.py``) para que el
cuerpo sea byte a byte el mismo que produciría el manejador central.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.api.middleware.context import build_request_context
from teaf._internal.api.models import ApiRequestContext
from teaf._internal.core.exceptions import ApplicationException
from teaf._internal.middleware.exception_handler import build_problem_response
from teaf._internal.runtime.event_bus import Event, EventBus


async def read_response_body(response: Response) -> bytes:
    """Materializa el cuerpo de ``response``, venga en memoria o como flujo.

    ``BaseHTTPMiddleware`` entrega siempre una respuesta en streaming, así
    que los middlewares que necesitan ver el cuerpo completo (compresión,
    idempotencia, validación de tamaño de respuesta) tienen que consumirlo.
    Hacerlo implica renunciar al streaming real para esas respuestas: es un
    coste asumido y documentado (ver docs/api/API-PROTECTION.md, "Coste de
    los middlewares que leen el cuerpo").
    """
    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        return bytes(response.body)
    chunks: list[bytes] = []
    async for chunk in body_iterator:
        chunks.append(bytes(chunk))
    return b"".join(chunks)


def rebuild_response(response: Response, body: bytes) -> Response:
    """Reconstruye ``response`` con ``body`` ya materializado, conservando sus cabeceras.

    ``Content-Length`` se recalcula siempre: mantener el de la respuesta
    original produciría respuestas truncadas o colgadas en cuanto el cuerpo
    cambie de tamaño (justo lo que hace la compresión).
    """
    headers = dict(response.headers)
    headers.pop("content-length", None)
    rebuilt = Response(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type=response.media_type,
    )
    rebuilt.background = response.background
    return rebuilt


class ApiProtectionMiddleware(BaseHTTPMiddleware):
    """Base de los middlewares de protección: contexto, eventos y rechazos uniformes."""

    def __init__(
        self,
        app: object,
        *,
        event_bus: EventBus | None = None,
        event_bus_provider: Callable[[], EventBus | None] | None = None,
        trust_forwarded_headers: bool = True,
    ) -> None:
        """``event_bus_provider`` existe por una razón de orden de arranque:
        ``ApiGateway.install()`` debe ejecutarse **antes** de que arranque el
        ciclo de vida ASGI (Starlette congela su pila de middlewares en el
        primer arranque), pero el ``EventBus`` pertenece al ``Runtime`` y solo
        aparece *durante* ese ciclo de vida, cuando el módulo recibe su
        ``ModuleContext``. Capturar el bus en el constructor lo dejaría fijado
        a ``None`` para siempre; resolverlo en cada publicación no.

        ``event_bus`` sigue disponible para quien construya un middleware a
        mano con un bus ya existente — tiene prioridad sobre el proveedor.
        """
        super().__init__(app)
        self._event_bus = event_bus
        self._event_bus_provider = event_bus_provider
        self._trust_forwarded_headers = trust_forwarded_headers

    @property
    def event_bus(self) -> EventBus | None:
        """``EventBus`` vigente: el explícito, el del proveedor, o ninguno."""
        if self._event_bus is not None:
            return self._event_bus
        return self._event_bus_provider() if self._event_bus_provider is not None else None

    def context_of(self, request: Request) -> ApiRequestContext:
        """``ApiRequestContext`` de ``request``, cacheado en el estado de la petición.

        La caché evita reconstruirlo en cada uno de los middlewares de la
        cadena — y, más importante, garantiza que todos vean exactamente la
        misma identidad y la misma IP, aunque un middleware intermedio
        cambiara el contexto de seguridad.
        """
        cached = getattr(request.state, "api_request_context", None)
        if isinstance(cached, ApiRequestContext):
            return cached
        context = build_request_context(
            request, trust_forwarded_headers=self._trust_forwarded_headers
        )
        request.state.api_request_context = context
        return context

    def publish(self, name: str, payload: dict[str, object]) -> None:
        """Publica un evento en el ``EventBus`` del Runtime, si hay alguno conectado."""
        bus = self.event_bus
        if bus is not None:
            bus.publish(Event(name=name, payload=payload))

    def reject(
        self,
        request: Request,
        exception: ApplicationException,
        *,
        headers: Mapping[str, str] | None = None,
        event_payload: dict[str, object] | None = None,
    ) -> Response:
        """Construye la respuesta de rechazo y publica ``request.rejected``."""
        payload: dict[str, object] = {
            "method": request.method,
            "path": request.url.path,
            "reason": exception.error_code,
        }
        payload.update(event_payload or {})
        self.publish("request.rejected", payload)
        return build_problem_response(exception, instance_path=request.url.path, headers=headers)
