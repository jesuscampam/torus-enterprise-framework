"""``ApiVersionMiddleware`` — negocia la versión de API de cada petición.

Deja el resultado en ``request.state.api_version`` para que cualquier
endpoint pueda leerlo sin volver a negociar, y añade a la respuesta las
cabeceras que informan de la versión servida y de su retirada
(``X-API-Version``, ``Deprecation``, ``Sunset``).

Que el middleware **no** enrute por versión es deliberado: elegir qué
implementación atiende cada versión es una decisión de la aplicación (dos
routers, una rama en el servicio, dos despliegues distintos), y un framework
que la impusiera limitaría más de lo que ayuda. Lo que TEAF garantiza es que
la versión esté resuelta, validada y comunicada (ver docs/api/VERSIONING.md).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from teaf._internal.api.exceptions import UnsupportedApiVersionException
from teaf._internal.api.middleware.base import ApiProtectionMiddleware
from teaf._internal.api.versioning.negotiator import ApiVersionNegotiator


class ApiVersionMiddleware(ApiProtectionMiddleware):
    """Resuelve la versión de API y la publica en la petición y en la respuesta."""

    def __init__(
        self, app: ASGIApp, *, negotiator: ApiVersionNegotiator, **base_options: Any
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
        if not self._negotiator.policy.enabled:
            return await call_next(request)

        try:
            negotiation = self._negotiator.negotiate(
                path=request.url.path, headers=dict(request.headers)
            )
        except UnsupportedApiVersionException as exc:
            return self.reject(request, exc, event_payload={"requested": exc.requested})

        request.state.api_version = negotiation
        self.publish("version.negotiated", negotiation.as_dict())

        response = await call_next(request)
        response.headers.update(self._negotiator.response_headers(negotiation))
        return response
