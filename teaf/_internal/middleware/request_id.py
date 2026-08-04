"""Middleware de Request ID / Correlation ID.

Propaga (o genera, si el cliente no lo envía) el correlation-id de cada
petición, lo expone al resto del framework vía ``backend/core/context.py``
y lo devuelve en la respuesta — ver docs/standards/LOGGING-STANDARD.md,
sección 2, y docs/diagrams/security-architecture.mmd.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.core.context import set_correlation_id
from teaf._internal.shared.constants import HEADER_CORRELATION_ID
from teaf._internal.shared.identifiers import new_uuid


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Asigna un correlation-id único a cada petición HTTP entrante."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get(HEADER_CORRELATION_ID) or new_uuid()
        set_correlation_id(correlation_id)

        response = await call_next(request)
        response.headers[HEADER_CORRELATION_ID] = correlation_id
        return response
