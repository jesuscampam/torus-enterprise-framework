"""Pruebas unitarias de teaf/_internal/observability/exporters/*."""

from __future__ import annotations

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from teaf._internal.observability.exporters.console import ConsoleExporter
from teaf._internal.observability.exporters.otlp import OtlpExporter
from teaf._internal.observability.exporters.prepared import (
    AzureMonitorExporter,
    DatadogExporter,
    DynatraceExporter,
    ElasticExporter,
    GrafanaExporter,
    JaegerExporter,
    NewRelicExporter,
    SplunkExporter,
    ZipkinExporter,
)
from teaf._internal.observability.exporters.prometheus import PrometheusExporter

_PREPARED_EXPORTERS = (
    (JaegerExporter, "jaeger"),
    (ZipkinExporter, "zipkin"),
    (DynatraceExporter, "dynatrace"),
    (ElasticExporter, "elastic"),
    (AzureMonitorExporter, "azure-monitor"),
    (GrafanaExporter, "grafana"),
    (DatadogExporter, "datadog"),
    (NewRelicExporter, "new-relic"),
    (SplunkExporter, "splunk"),
)


def test_console_exporter_name() -> None:
    assert ConsoleExporter().name == "console"


def test_console_exporter_attaches_a_span_processor_to_a_real_tracer_provider() -> None:
    provider = TracerProvider()
    ConsoleExporter().configure_tracing(provider)
    with provider.get_tracer("test").start_as_current_span("op"):
        pass
    provider.shutdown()


def test_console_exporter_appends_a_metric_reader() -> None:
    readers: list[object] = []
    ConsoleExporter().configure_metrics(readers)
    assert len(readers) == 1


def test_otlp_exporter_name() -> None:
    assert OtlpExporter().name == "otlp"


def test_otlp_exporter_attaches_a_batch_span_processor() -> None:
    provider = TracerProvider()
    OtlpExporter(traces_endpoint="http://localhost:4318/v1/traces").configure_tracing(provider)
    provider.shutdown()


def test_otlp_exporter_appends_a_metric_reader() -> None:
    readers: list[object] = []
    OtlpExporter(metrics_endpoint="http://localhost:4318/v1/metrics").configure_metrics(readers)
    assert len(readers) == 1


def test_prometheus_exporter_name() -> None:
    assert PrometheusExporter().name == "prometheus"


def test_prometheus_exporter_configure_tracing_is_a_documented_no_op() -> None:
    provider = TracerProvider()
    PrometheusExporter().configure_tracing(provider)  # must not raise


def test_prometheus_exporter_appends_its_reader_bound_to_its_own_registry() -> None:
    exporter = PrometheusExporter()
    readers: list[object] = []
    exporter.configure_metrics(readers)
    assert len(readers) == 1

    provider = MeterProvider(metric_readers=readers)
    counter = provider.get_meter("test").create_counter("orders_created_total")
    counter.add(1)
    provider.force_flush()

    metric_families = list(exporter.registry.collect())
    sample_names = {sample.name for family in metric_families for sample in family.samples}
    assert "orders_created_total" in sample_names


@pytest.mark.parametrize("exporter_cls,expected_name", _PREPARED_EXPORTERS)
def test_prepared_exporters_expose_a_stable_name(exporter_cls: type, expected_name: str) -> None:
    assert exporter_cls().name == expected_name


@pytest.mark.parametrize("exporter_cls,_expected_name", _PREPARED_EXPORTERS)
def test_prepared_exporters_raise_not_implemented_on_configure_tracing(
    exporter_cls: type, _expected_name: str
) -> None:
    exporter = exporter_cls()
    with pytest.raises(NotImplementedError, match=exporter.name):
        exporter.configure_tracing(TracerProvider())


@pytest.mark.parametrize("exporter_cls,_expected_name", _PREPARED_EXPORTERS)
def test_prepared_exporters_raise_not_implemented_on_configure_metrics(
    exporter_cls: type, _expected_name: str
) -> None:
    exporter = exporter_cls()
    with pytest.raises(NotImplementedError, match=exporter.name):
        exporter.configure_metrics([])


def test_console_and_otlp_exporters_together_do_not_interfere_with_a_real_span_export() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    ConsoleExporter().configure_tracing(provider)

    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with provider.get_tracer("test").start_as_current_span("op"):
        pass
    assert len(exporter.get_finished_spans()) == 1


def test_console_exporter_metric_reader_produces_real_data() -> None:
    readers: list[object] = []
    ConsoleExporter().configure_metrics(readers)
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    counter = provider.get_meter("test").create_counter("checks_total")
    counter.add(1)
    data = reader.get_metrics_data()
    assert data is not None
