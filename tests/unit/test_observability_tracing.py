"""Pruebas unitarias de teaf/_internal/observability/tracing/tracer.py (OtelTracer/OtelSpan)."""

from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from teaf._internal.core.context import get_span_id, get_trace_id
from teaf._internal.observability.models import SpanKind, SpanStatus
from teaf._internal.observability.tracing.tracer import OtelTracer


def _build_tracer() -> tuple[OtelTracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return OtelTracer(provider.get_tracer("test")), exporter


def test_start_span_yields_a_span_with_real_hex_ids() -> None:
    tracer, _ = _build_tracer()
    with tracer.start_span("op") as span:
        assert len(span.trace_id) == 32
        assert len(span.span_id) == 16
        int(span.trace_id, 16)
        int(span.span_id, 16)


def test_start_span_synchronizes_core_context_while_active_and_restores_after() -> None:
    tracer, _ = _build_tracer()
    assert get_trace_id() is None
    with tracer.start_span("op") as span:
        assert get_trace_id() == span.trace_id
        assert get_span_id() == span.span_id
    assert get_trace_id() is None
    assert get_span_id() is None


def test_nested_spans_restore_the_parent_context_on_exit() -> None:
    tracer, _ = _build_tracer()
    with tracer.start_span("outer") as outer:
        with tracer.start_span("inner") as inner:
            assert get_span_id() == inner.span_id
            assert inner.trace_id == outer.trace_id
        assert get_span_id() == outer.span_id


def test_set_attribute_add_event_and_status_are_recorded_on_the_exported_span() -> None:
    tracer, exporter = _build_tracer()
    with tracer.start_span("op") as span:
        span.set_attribute("http.method", "GET")
        span.add_event("cache.miss", attributes={"key": "abc"})
        span.set_status(SpanStatus.OK)

    exported = exporter.get_finished_spans()[0]
    assert exported.attributes["http.method"] == "GET"
    assert exported.events[0].name == "cache.miss"
    assert exported.events[0].attributes["key"] == "abc"
    assert exported.status.status_code.name == "OK"


def test_record_exception_marks_the_span_as_error() -> None:
    tracer, exporter = _build_tracer()
    with tracer.start_span("op") as span:
        span.record_exception(ValueError("boom"))

    exported = exporter.get_finished_spans()[0]
    assert exported.status.status_code.name == "ERROR"
    assert exported.events[0].name == "exception"


def test_start_span_accepts_a_kind() -> None:
    tracer, exporter = _build_tracer()
    with tracer.start_span("op", kind=SpanKind.SERVER):
        pass

    exported = exporter.get_finished_spans()[0]
    assert exported.kind.name == "SERVER"


def test_links_reference_another_span_without_making_it_the_parent() -> None:
    tracer, exporter = _build_tracer()
    with tracer.start_span("linked") as linked_span:
        pass

    with tracer.start_span("op", links=(linked_span,)):
        pass

    exported = next(s for s in exporter.get_finished_spans() if s.name == "op")
    assert exported.parent is None
    assert len(exported.links) == 1
    assert format(exported.links[0].context.trace_id, "032x") == linked_span.trace_id
