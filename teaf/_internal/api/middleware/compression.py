"""``CompressionMiddleware`` — comprime la respuesta según ``Accept-Encoding``.

Nunca comprime una respuesta que ya viene comprimida (``Content-Encoding``
presente) ni una que el negociador descarte por tamaño o tipo. Y si el
resultado comprimido no es más pequeño que el original —cosa que ocurre con
contenido ya empaquetado o muy corto— se devuelve el original: comprimir
para agrandar sería trabajo puro de CPU a cambio de más bytes en red.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.api.compression.providers import CompressionNegotiator
from teaf._internal.api.middleware.base import (
    ApiProtectionMiddleware,
    read_response_body,
    rebuild_response,
)


class CompressionMiddleware(ApiProtectionMiddleware):
    """Aplica GZip/Brotli a las respuestas que lo admitan."""

    def __init__(
        self, app: object, *, negotiator: CompressionNegotiator, **base_options: Any
    ) -> None:
        """``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._negotiator = negotiator

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        if not self._negotiator.policy.enabled or not self._negotiator.providers:
            return response
        if response.headers.get("content-encoding"):
            return response

        body = await read_response_body(response)
        provider = self._negotiator.select(
            accept_encoding=request.headers.get("accept-encoding", ""),
            content_type=response.headers.get("content-type"),
            content_length=len(body),
        )
        if provider is None:
            return rebuild_response(response, body)

        compressed = provider.compress(body)
        if len(compressed) >= len(body):
            return rebuild_response(response, body)

        rebuilt = rebuild_response(response, compressed)
        rebuilt.headers["Content-Encoding"] = provider.algorithm.value
        # Sin "Vary: Accept-Encoding" una caché intermedia podría servir la
        # respuesta comprimida a un cliente que no anunció soportarla.
        existing_vary = response.headers.get("vary")
        rebuilt.headers["Vary"] = (
            f"{existing_vary}, Accept-Encoding" if existing_vary else "Accept-Encoding"
        )
        self.publish(
            "request.compressed",
            {
                "path": request.url.path,
                "algorithm": provider.algorithm.value,
                "originalBytes": len(body),
                "compressedBytes": len(compressed),
            },
        )
        return rebuilt
