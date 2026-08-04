"""``ObservabilityMiddleware`` — abre un span raíz y mide la duración de cada petición HTTP.

Mismo patrón que ``middleware/request_id.py``/``security/middleware.py``
(``BaseHTTPMiddleware``, cableado manual vía ``app.asgi.add_middleware(...)``
— ``ObservabilityModule`` no se auto-registra, igual que ``SecurityModule``,
ver ``docs/public-api/PUBLIC-API.md``).

``OtelTracer.start_span`` (``observability/tracing/tracer.py``) ya
sincroniza ``core/context.py`` con el trace-id/span-id del span mientras
está activo — así todo log emitido durante la petición (``JsonFormatter``,
``core/logging.py``) incluye el trace-id/span-id correctos sin que este
middleware, ni ``core/logging.py``, necesiten conocerse entre sí.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from teaf._internal.contracts.telemetry import Histogram, Meter, Tracer
from teaf._internal.observability.models import SpanKind, SpanStatus
from teaf._internal.runtime.event_bus import Event, EventBus


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Abre un span ``SERVER`` por petición y registra su duración como histograma."""

    def __init__(
        self, app: object, *, tracer: Tracer, meter: Meter, event_bus: EventBus | None = None
    ) -> None:
        super().__init__(app)
        self._tracer = tracer
        self._event_bus = event_bus
        self._request_duration: Histogram = meter.create_histogram(
            "http.server.request.duration",
            unit="s",
            description="Duración de cada petición HTTP servida, en segundos.",
        )

    def _publish(self, name: str, payload: dict[str, object]) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(Event(name=name, payload=payload))

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started_at = time.perf_counter()
        with self._tracer.start_span(
            f"{request.method} {request.url.path}",
            kind=SpanKind.SERVER,
            attributes={
                "http.request.method": request.method,
                "url.path": request.url.path,
            },
        ) as span:
            self._publish("trace.started", {"traceId": span.trace_id, "spanId": span.span_id})
            try:
                response = await call_next(request)
            except Exception as exc:
                span.record_exception(exc)
                self._publish(
                    "trace.finished",
                    {"traceId": span.trace_id, "spanId": span.span_id, "statusCode": None},
                )
                raise

            span.set_attribute("http.response.status_code", response.status_code)
            span.set_status(SpanStatus.OK if response.status_code < 500 else SpanStatus.ERROR)
            self._publish(
                "trace.finished",
                {
                    "traceId": span.trace_id,
                    "spanId": span.span_id,
                    "statusCode": response.status_code,
                },
            )

        duration_seconds = time.perf_counter() - started_at
        self._request_duration.record(
            duration_seconds,
            attributes={
                "http.request.method": request.method,
                "url.path": request.url.path,
                "http.response.status_code": response.status_code,
            },
        )
        self._publish(
            "metric.recorded",
            {"name": "http.server.request.duration", "value": duration_seconds},
        )
        return response
