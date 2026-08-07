"""``IdempotencyMiddleware`` — reproduce la respuesta original de un reintento.

Es el middleware más interno de la cadena, pegado al endpoint, por una razón
concreta: la respuesta que guarda debe ser la que produjo el *handler*, sin
compresión aplicada ni cabeceras añadidas por capas exteriores. Guardar una
respuesta ya comprimida obligaría a reproducirla comprimida incluso a un
cliente que no admita esa codificación.

Lee el cuerpo de la petición para calcular la huella, y lo repone en el
``receive`` de la petición para que el endpoint pueda volver a leerlo — sin
eso, todo endpoint con cuerpo detrás de este middleware recibiría un cuerpo
vacío.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message

from teaf._internal.api.exceptions import IdempotencyConflictException
from teaf._internal.api.idempotency.manager import IdempotencyManager, build_fingerprint
from teaf._internal.api.middleware.audit import IDEMPOTENT_REPLAY_HEADER
from teaf._internal.api.middleware.base import (
    ApiProtectionMiddleware,
    read_response_body,
    rebuild_response,
)


class IdempotencyMiddleware(ApiProtectionMiddleware):
    """Detecta reintentos por ``Idempotency-Key`` y devuelve la respuesta original."""

    def __init__(self, app: object, *, manager: IdempotencyManager, **base_options: Any) -> None:
        """``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._manager = manager

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        key = request.headers.get(self._manager.header_name)
        if not key or not self._manager.applies_to(request.method):
            return await call_next(request)

        body = await request.body()
        _restore_request_body(request, body)
        fingerprint = build_fingerprint(method=request.method, path=request.url.path, body=body)

        try:
            existing = await self._manager.lookup(key, fingerprint=fingerprint)
        except IdempotencyConflictException as exc:
            return self.reject(request, exc, event_payload={"idempotencyKey": key})

        if existing is not None:
            self.publish(
                "idempotency.detected",
                {"key": key, "path": request.url.path, "statusCode": existing.status_code},
            )
            replayed = Response(
                content=existing.body,
                status_code=existing.status_code,
                headers=dict(existing.headers),
            )
            replayed.headers[IDEMPOTENT_REPLAY_HEADER] = "true"
            return replayed

        response = await call_next(request)
        response_body = await read_response_body(response)
        await self._manager.remember(
            key,
            fingerprint=fingerprint,
            status_code=response.status_code,
            body=response_body,
            headers={
                name: value
                for name, value in response.headers.items()
                # ``content-length`` se recalcula al reproducir; conservarlo
                # aquí produciría una respuesta con longitud incoherente.
                if name.lower() != "content-length"
            },
        )
        return rebuild_response(response, response_body)


def _restore_request_body(request: Request, body: bytes) -> None:
    """Repone ``body`` en el ``receive`` de ``request`` para que el endpoint pueda leerlo.

    ``Request.body()`` consume el flujo ASGI: sin reponerlo, el endpoint
    recibiría un cuerpo vacío. Starlette cachea el cuerpo en
    ``request._body``, pero esa caché no viaja al objeto ``Request`` que
    construye la capa siguiente — el ``receive`` sí.
    """

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive  # noqa: SLF001 — no hay API pública equivalente en Starlette
