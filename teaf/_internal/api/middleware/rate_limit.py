"""``RateLimitMiddleware`` — aplica las reglas de ``RateLimiter`` a cada petición.

Añade siempre las cabeceras ``X-RateLimit-*`` a la respuesta, se acepte o se
rechace: un cliente bien educado usa ``X-RateLimit-Remaining`` para
autorregularse *antes* de chocar contra el límite, y solo puede hacerlo si
esa información viaja también en las respuestas correctas.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.api.exceptions import RateLimitExceededException
from teaf._internal.api.middleware.base import ApiProtectionMiddleware
from teaf._internal.api.models import RateLimitDecision
from teaf._internal.api.ratelimit.limiter import RateLimiter


def rate_limit_headers(decision: RateLimitDecision) -> dict[str, str]:
    """Cabeceras ``X-RateLimit-*`` (y ``Retry-After`` si procede) de ``decision``."""
    headers = {
        "X-RateLimit-Limit": str(decision.limit),
        "X-RateLimit-Remaining": str(decision.remaining),
        "X-RateLimit-Reset": str(int(decision.reset_after_seconds)),
    }
    if not decision.allowed:
        headers["Retry-After"] = str(retry_after_seconds(decision))
    return headers


def retry_after_seconds(decision: RateLimitDecision) -> int:
    """Segundos enteros a esperar, redondeados **hacia arriba**.

    Decirle al cliente que espere 0 segundos cuando en realidad faltan 0,4 lo
    haría reintentar de inmediato y volver a chocar contra el mismo límite.
    Lo usan tanto la cabecera ``Retry-After`` como el mensaje del error, para
    que ambos digan exactamente lo mismo.
    """
    return max(1, math.ceil(decision.retry_after_seconds))


class RateLimitMiddleware(ApiProtectionMiddleware):
    """Rechaza con HTTP 429 las peticiones que superan alguna regla de limitación."""

    def __init__(self, app: object, *, limiter: RateLimiter, **base_options: Any) -> None:
        """``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._limiter = limiter

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self._limiter.enabled:
            return await call_next(request)

        context = self.context_of(request)
        denial = await self._limiter.acquire(context)

        if denial is not None:
            self.publish("rate.limit.exceeded", denial.as_dict())
            return self.reject(
                request,
                RateLimitExceededException(
                    f"Se superó el límite de peticiones de la regla '{denial.rule}'. "
                    f"Reintenta en {retry_after_seconds(denial)} segundos.",
                    rule=denial.rule,
                    retry_after_seconds=denial.retry_after_seconds,
                ),
                headers=rate_limit_headers(denial),
                event_payload={"rule": denial.rule},
            )

        response = await call_next(request)

        # Estado tras consumir la petición: ``inspect()`` no consume cuota, así
        # que informar de él es gratis y deja al cliente ver cuánto le queda.
        # Con varias reglas activas se informa de la más restrictiva (la de
        # menor ``remaining``): es la que el cliente va a chocar primero.
        decisions = await self._limiter.inspect(context)
        if decisions:
            tightest = min(decisions, key=lambda d: d.remaining)
            response.headers.update(rate_limit_headers(tightest))
        return response
