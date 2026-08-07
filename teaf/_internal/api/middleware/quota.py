"""``QuotaMiddleware`` — aplica las cuotas de ``QuotaManager`` a cada petición.

El ``finally`` que llama a ``release()`` no es opcional: las cuotas de
concurrencia suben al aceptar la petición y solo bajan al terminarla. Sin
ese ``finally``, una excepción en el endpoint dejaría el contador alto para
siempre y la cuota se agotaría sola tras suficientes errores.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.api.exceptions import QuotaExceededException
from teaf._internal.api.middleware.base import ApiProtectionMiddleware
from teaf._internal.api.models import QuotaDecision
from teaf._internal.api.quotas.manager import QuotaManager


def quota_headers(decision: QuotaDecision) -> dict[str, str]:
    """Cabeceras ``X-Quota-*`` (y ``Retry-After`` si procede) de ``decision``."""
    usage = decision.usage
    headers = {
        "X-Quota-Limit": str(usage.limit),
        "X-Quota-Remaining": str(int(usage.remaining)),
        "X-Quota-Period": usage.period.value,
    }
    if not decision.allowed and decision.retry_after_seconds > 0:
        headers["Retry-After"] = str(max(1, int(decision.retry_after_seconds)))
    return headers


class QuotaMiddleware(ApiProtectionMiddleware):
    """Rechaza con HTTP 429 las peticiones que agotan alguna cuota."""

    def __init__(self, app: object, *, manager: QuotaManager, **base_options: Any) -> None:
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
        if not self._manager.enabled or not self._manager.rules:
            return await call_next(request)

        context = self.context_of(request)
        denial = await self._manager.consume(context)

        if denial is not None:
            self.publish("quota.exceeded", denial.as_dict())
            return self.reject(
                request,
                QuotaExceededException(
                    f"Se agotó la cuota '{denial.usage.rule}' "
                    f"({denial.usage.consumed:.0f}/{denial.usage.limit} "
                    f"por {denial.usage.period.value}).",
                    rule=denial.usage.rule,
                    retry_after_seconds=denial.retry_after_seconds,
                ),
                headers=quota_headers(denial),
                event_payload={"rule": denial.usage.rule},
            )

        try:
            return await call_next(request)
        finally:
            await self._manager.release(context)
