"""Middleware de logging de peticiones.

Registra entrada/salida de cada petición HTTP (método, ruta, status,
duración) en ``INFO``, conforme a docs/standards/LOGGING-STANDARD.md,
sección 5 ("middleware/ registra entrada/salida de cada petición HTTP").
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.core.logging import get_logger

_logger = get_logger("teaf.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Loguea el inicio y el resultado de cada petición HTTP."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started_at = time.perf_counter()
        _logger.info(
            "request_started",
            extra={"context": {"method": request.method, "path": request.url.path}},
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _logger.info(
            "request_completed",
            extra={
                "context": {
                    "method": request.method,
                    "path": request.url.path,
                    "statusCode": response.status_code,
                    "durationMs": duration_ms,
                }
            },
        )
        return response
