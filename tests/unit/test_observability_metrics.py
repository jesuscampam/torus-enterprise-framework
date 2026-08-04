"""Pruebas unitarias de teaf/_internal/observability/metrics/meter.py (OtelMeter)."""

from __future__ import annotations

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from teaf._internal.observability.metrics.meter import OtelMeter


def _build_meter() -> tuple[OtelMeter, InMemoryMetricReader]:
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    return OtelMeter(provider.get_meter("test")), reader


def _metric_names(reader: InMemoryMetricReader) -> set[str]:
    data = reader.get_metrics_data()
    names: set[str] = set()
    if data is None:
        return names
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                names.add(metric.name)
    return names


def test_create_counter_records_and_exports() -> None:
    meter, reader = _build_meter()
    counter = meter.create_counter("requests_total", unit="1", description="total requests")
    counter.add(1, attributes={"route": "/health"})
    counter.add(2)
    assert "requests_total" in _metric_names(reader)


def test_create_up_down_counter_records_and_exports() -> None:
    meter, reader = _build_meter()
    gauge_like = meter.create_up_down_counter("active_connections")
    gauge_like.add(5)
    gauge_like.add(-2)
    assert "active_connections" in _metric_names(reader)


def test_create_histogram_records_and_exports() -> None:
    meter, reader = _build_meter()
    histogram = meter.create_histogram("request_duration_seconds", unit="s")
    histogram.record(0.42, attributes={"status": "200"})
    assert "request_duration_seconds" in _metric_names(reader)


def test_create_gauge_records_and_exports() -> None:
    meter, reader = _build_meter()
    gauge = meter.create_gauge("queue_size")
    gauge.set(7)
    assert "queue_size" in _metric_names(reader)
