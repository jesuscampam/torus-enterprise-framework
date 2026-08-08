"""``ApiAuditMiddleware`` — registra en auditoría toda petición servida.

Se coloca casi en el exterior de la cadena de protección (solo CORS queda
por fuera) precisamente para ver *todo*: las peticiones aceptadas, las
rechazadas por rate limiting o cuotas, y las que terminaron en excepción.
Una auditoría que solo viera el tráfico aceptado sería inútil para lo que
más importa auditar.

Publica ``request.accepted`` para las respuestas correctas; los rechazos ya
publican ``request.rejected`` desde el middleware que los emitió, así que
aquí no se vuelven a anunciar (se duplicarían en el bus).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from teaf._internal.api.audit.audit import ApiAudit, build_audit_record
from teaf._internal.api.middleware.base import ApiProtectionMiddleware
from teaf._internal.api.models import ApiOutcome, VersionNegotiation

#: Cabecera con la que ``IdempotencyMiddleware`` marca una respuesta
#: reproducida, para que la auditoría la distinga de una ejecución real.
IDEMPOTENT_REPLAY_HEADER = "X-Idempotent-Replay"


class ApiAuditMiddleware(ApiProtectionMiddleware):
    """Construye y registra un ``ApiAuditRecord`` por cada petición."""

    def __init__(self, app: ASGIApp, *, audit: ApiAudit, **base_options: Any) -> None:
        """``base_options`` son los argumentos comunes de
        ``ApiProtectionMiddleware`` (``event_bus``/``event_bus_provider``/
        ``trust_forwarded_headers``): se reenvían tal cual en vez de
        repetirlos en las ocho firmas, para que ampliar la base no obligue
        a tocar cada middleware."""
        super().__init__(app, **base_options)
        self._audit = audit

    def _resolve_outcome(self, response: Response) -> ApiOutcome:
        if response.headers.get(IDEMPOTENT_REPLAY_HEADER) == "true":
            return ApiOutcome.REPLAYED
        if response.status_code >= 500:
            return ApiOutcome.FAILED
        if response.status_code >= 400:
            return ApiOutcome.REJECTED
        return ApiOutcome.ACCEPTED

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self._audit.enabled:
            return await call_next(request)

        context = self.context_of(request)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            # Una excepción no controlada también se audita: es justo el caso
            # en el que más falta hace el registro. Se re-lanza intacta para
            # que el manejador central produzca la respuesta 500 de siempre.
            await self._audit.record(
                build_audit_record(
                    context,
                    status_code=500,
                    latency_seconds=time.perf_counter() - started_at,
                    outcome=ApiOutcome.FAILED,
                    reason=exc.__class__.__name__,
                )
            )
            raise

        latency_seconds = time.perf_counter() - started_at
        outcome = self._resolve_outcome(response)

        negotiation = getattr(request.state, "api_version", None)
        api_version = (
            str(negotiation.version) if isinstance(negotiation, VersionNegotiation) else None
        )
        content_length = response.headers.get("content-length")

        await self._audit.record(
            build_audit_record(
                context,
                status_code=response.status_code,
                latency_seconds=latency_seconds,
                outcome=outcome,
                response_bytes=int(content_length) if content_length else 0,
                api_version=api_version,
            )
        )

        if outcome is ApiOutcome.ACCEPTED:
            self.publish(
                "request.accepted",
                {
                    "method": context.method,
                    "path": context.path,
                    "statusCode": response.status_code,
                    "latencySeconds": round(latency_seconds, 6),
                },
            )
        return response
