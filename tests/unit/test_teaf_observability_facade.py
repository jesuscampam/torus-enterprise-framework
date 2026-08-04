"""Pruebas de la fachada pública ``teaf.observability`` (Sprint 2.8, ADR-008).

Mismo criterio que ``tests/unit/test_teaf_security_facade.py``: la
superficie pública es intencional, no accidental — se verifica de forma
explícita, no se infiere.
"""

from __future__ import annotations

import teaf
import teaf.observability

_EXPECTED_ALL = {
    "Tracer",
    "Span",
    "Meter",
    "Counter",
    "UpDownCounter",
    "Histogram",
    "Gauge",
    "Exporter",
    "TelemetryProvider",
    "OtelTracer",
    "OtelSpan",
    "OtelMeter",
    "OtelCounter",
    "OtelUpDownCounter",
    "OtelHistogram",
    "OtelGauge",
    "ConsoleExporter",
    "OtlpExporter",
    "PrometheusExporter",
    "PreparedExporter",
    "JaegerExporter",
    "ZipkinExporter",
    "DynatraceExporter",
    "ElasticExporter",
    "AzureMonitorExporter",
    "GrafanaExporter",
    "DatadogExporter",
    "NewRelicExporter",
    "SplunkExporter",
    "SpanKind",
    "SpanStatus",
    "HealthCheck",
    "HealthReport",
    "HealthStatus",
    "CompositeHealthChecker",
    "DiagnosticReport",
    "build_diagnostic_report",
    "get_logger",
    "TraceContext",
    "TelemetryContext",
    "get_telemetry_context",
    "set_telemetry_context",
    "ObservabilityMiddleware",
}


def test_all_is_defined_explicitly() -> None:
    assert hasattr(teaf.observability, "__all__")
    assert isinstance(teaf.observability.__all__, list)


def test_all_matches_the_expected_public_surface_exactly() -> None:
    assert set(teaf.observability.__all__) == _EXPECTED_ALL


def test_all_has_no_duplicates() -> None:
    assert len(teaf.observability.__all__) == len(set(teaf.observability.__all__))


def test_every_symbol_in_all_is_actually_importable() -> None:
    for name in teaf.observability.__all__:
        assert hasattr(teaf.observability, name), f"'{name}' está en __all__ pero no es un atributo"


def test_every_observability_symbol_is_also_reexported_from_top_level_teaf() -> None:
    """``from teaf import Tracer`` funciona igual que ``from teaf.observability import ...``
    — ver la nota de Sprint 2.8 en el docstring de ``teaf/__init__.py``."""
    for name in _EXPECTED_ALL:
        assert hasattr(teaf, name), f"'{name}' no se reexporta desde 'teaf' de nivel superior"
        assert getattr(teaf, name) is getattr(teaf.observability, name)


def test_observability_module_is_not_exposed_from_the_public_facade() -> None:
    """``ObservabilityModule`` se queda privado — mismo criterio que
    ``DatabaseModule``/``SecurityModule`` (ver docs/public-api/PUBLIC-API.md, sección 6)."""
    assert "ObservabilityModule" not in teaf.observability.__all__
    assert not hasattr(teaf.observability, "ObservabilityModule")
    assert not hasattr(teaf, "ObservabilityModule")


def test_health_status_is_the_same_alias_as_teaf_health() -> None:
    """Ver la nota de nomenclatura en el docstring de ``teaf/observability.py``:
    ``HealthStatus`` no duplica ``teaf.Health``, es el mismo alias reexportado."""
    assert teaf.observability.HealthStatus is teaf.Health


def test_trace_context_is_an_alias_of_telemetry_context_not_a_distinct_class() -> None:
    assert teaf.observability.TraceContext is teaf.observability.TelemetryContext


def test_otel_implementations_satisfy_their_contracts() -> None:
    assert issubclass(teaf.observability.OtelTracer, teaf.observability.Tracer)
    assert issubclass(teaf.observability.OtelSpan, teaf.observability.Span)
    assert issubclass(teaf.observability.OtelMeter, teaf.observability.Meter)
    assert issubclass(teaf.observability.OtelCounter, teaf.observability.Counter)
    assert issubclass(teaf.observability.OtelHistogram, teaf.observability.Histogram)
    assert issubclass(teaf.observability.OtelGauge, teaf.observability.Gauge)
    assert issubclass(teaf.observability.OtelUpDownCounter, teaf.observability.UpDownCounter)


def test_all_exporters_satisfy_the_exporter_contract() -> None:
    exporter_names = (
        "ConsoleExporter",
        "OtlpExporter",
        "PrometheusExporter",
        "JaegerExporter",
        "ZipkinExporter",
        "DynatraceExporter",
        "ElasticExporter",
        "AzureMonitorExporter",
        "GrafanaExporter",
        "DatadogExporter",
        "NewRelicExporter",
        "SplunkExporter",
    )
    for name in exporter_names:
        exporter_cls = getattr(teaf.observability, name)
        assert issubclass(exporter_cls, teaf.observability.Exporter)
