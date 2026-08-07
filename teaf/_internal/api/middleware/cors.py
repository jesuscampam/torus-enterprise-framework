"""``CorsMiddleware`` — aplica una ``CorsPolicy`` sobre las peticiones cruzadas.

Es el middleware más externo de la cadena, y tiene que serlo: las cabeceras
CORS deben viajar también en las respuestas de error. Si quedara por dentro
del limitador, un 429 saldría sin ``Access-Control-Allow-Origin`` y el
navegador se lo ocultaría al cliente como un error de red genérico — el
desarrollador vería "failed to fetch" en lugar de "te has pasado de
peticiones", que es un fallo de diagnóstico muy caro y muy común.

Las peticiones sin cabecera ``Origin`` (mismo origen, o clientes que no son
navegadores) pasan intactas: CORS es un mecanismo del navegador, y añadirle
cabeceras a quien no las pidió solo añade ruido.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp

from teaf._internal.api.cors.policy import CorsPolicy
from teaf._internal.api.middleware.base import ApiProtectionMiddleware


class CorsMiddleware(ApiProtectionMiddleware):
    """Responde los preflight ``OPTIONS`` y añade cabeceras CORS al resto de respuestas."""

    def __init__(self, app: ASGIApp, *, policy: CorsPolicy, **base_options: Any) -> None:
        """``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._policy = policy

    @property
    def policy(self) -> CorsPolicy:
        """Política aplicada por este middleware."""
        return self._policy

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        if not self._policy.enabled or origin is None:
            return await call_next(request)

        if request.method == "OPTIONS" and "access-control-request-method" in request.headers:
            return self._handle_preflight(request, origin)

        response = await call_next(request)
        response.headers.update(self._policy.response_headers(origin))
        return response

    def _handle_preflight(self, request: Request, origin: str) -> Response:
        requested_method = request.headers.get("access-control-request-method", "")
        requested_headers = [
            header
            for header in request.headers.get("access-control-request-headers", "").split(",")
            if header.strip()
        ]
        headers = self._policy.preflight_headers(
            origin, request_method=requested_method, request_headers=requested_headers
        )
        if headers is None:
            self.publish(
                "request.rejected",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "reason": "cors-origin-not-allowed",
                    "origin": origin,
                },
            )
            # 403 con cuerpo de texto plano y sin cabeceras CORS: es lo que el
            # navegador interpreta como "preflight rechazado". Deliberadamente
            # no se usa RFC 7807 aquí — el navegador nunca muestra este cuerpo
            # al código cliente, así que un problem+json solo confundiría a
            # quien lo lea en una traza de red.
            return PlainTextResponse("CORS origin not allowed", status_code=403)

        # 204 sin cuerpo: la respuesta canónica a un preflight aceptado.
        return Response(status_code=204, headers=headers)
