"""``OtelTracer``/``OtelSpan`` — implementación de ``Tracer``/``Span`` sobre OpenTelemetry.

Cada span nuevo sincroniza ``core/context.py`` con su trace-id/span-id
mientras está activo (y lo restaura al salir) — así ``JsonFormatter``
(``core/logging.py``) incluye el trace-id/span-id correctos en cada log
emitido dentro del span, sin que ``core/logging.py`` conozca OpenTelemetry
(ver ADR-008).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

from opentelemetry import trace as otel_trace
from opentelemetry.trace import Link as OtelLink
from opentelemetry.trace import SpanContext as OtelSpanContext
from opentelemetry.trace import SpanKind as OtelSpanKind
from opentelemetry.trace import Status as OtelStatus
from opentelemetry.trace import StatusCode as OtelStatusCode
from opentelemetry.trace import TraceFlags

from teaf._internal.contracts.telemetry import Span, Tracer
from teaf._internal.core.context import get_span_id, get_trace_id, set_trace_context
from teaf._internal.observability.models import SpanKind, SpanStatus

_SPAN_KIND_MAP: dict[SpanKind, OtelSpanKind] = {
    SpanKind.INTERNAL: OtelSpanKind.INTERNAL,
    SpanKind.SERVER: OtelSpanKind.SERVER,
    SpanKind.CLIENT: OtelSpanKind.CLIENT,
    SpanKind.PRODUCER: OtelSpanKind.PRODUCER,
    SpanKind.CONSUMER: OtelSpanKind.CONSUMER,
}

_SPAN_STATUS_MAP: dict[SpanStatus, OtelStatusCode] = {
    SpanStatus.UNSET: OtelStatusCode.UNSET,
    SpanStatus.OK: OtelStatusCode.OK,
    SpanStatus.ERROR: OtelStatusCode.ERROR,
}


class OtelSpan(Span):
    """Envuelve un ``opentelemetry.trace.Span`` real."""

    def __init__(self, span: otel_trace.Span) -> None:
        self._span = span

    @property
    def trace_id(self) -> str:
        return format(self._span.get_span_context().trace_id, "032x")

    @property
    def span_id(self) -> str:
        return format(self._span.get_span_context().span_id, "016x")

    def set_attribute(self, key: str, value: str | bool | int | float) -> None:
        self._span.set_attribute(key, value)

    def add_event(self, name: str, *, attributes: Mapping[str, object] | None = None) -> None:
        self._span.add_event(name, attributes=dict(attributes) if attributes else None)

    def record_exception(self, exception: BaseException) -> None:
        self._span.record_exception(exception)
        self._span.set_status(OtelStatus(OtelStatusCode.ERROR, str(exception)))

    def set_status(self, status: SpanStatus, description: str | None = None) -> None:
        self._span.set_status(OtelStatus(_SPAN_STATUS_MAP[status], description))


def _as_otel_link(span: Span) -> OtelLink:
    """Traduce un ``Span`` de TEAF (ya finalizado o de otra traza) a un ``Link`` de OTel."""
    context = OtelSpanContext(
        trace_id=int(span.trace_id, 16),
        span_id=int(span.span_id, 16),
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    return OtelLink(context)


class OtelTracer(Tracer):
    """Envuelve un ``opentelemetry.trace.Tracer`` real."""

    def __init__(self, tracer: otel_trace.Tracer) -> None:
        self._tracer = tracer

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Mapping[str, object] | None = None,
        links: Sequence[Span] = (),
    ) -> Iterator[Span]:
        with self._tracer.start_as_current_span(
            name,
            kind=_SPAN_KIND_MAP[kind],
            attributes=dict(attributes) if attributes else None,
            links=[_as_otel_link(link) for link in links],
        ) as otel_span:
            wrapped = OtelSpan(otel_span)
            previous_trace_id, previous_span_id = get_trace_id(), get_span_id()
            set_trace_context(trace_id=wrapped.trace_id, span_id=wrapped.span_id)
            try:
                yield wrapped
            finally:
                set_trace_context(trace_id=previous_trace_id, span_id=previous_span_id)
