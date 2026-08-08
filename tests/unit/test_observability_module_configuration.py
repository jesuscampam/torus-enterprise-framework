"""Pruebas unitarias de teaf/_internal/modules/observability/configuration.py."""

from __future__ import annotations

from teaf._internal.modules.observability.configuration import ObservabilityConfiguration


def test_defaults_produce_a_working_out_of_the_box_configuration() -> None:
    config = ObservabilityConfiguration()
    assert config.service_name == "teaf"
    assert config.console_exporter_enabled is True
    assert config.otlp_exporter_enabled is False
    assert config.prometheus_exporter_enabled is False
    assert config.sampling_ratio == 1.0


def test_from_mapping_with_empty_mapping_uses_all_defaults() -> None:
    config = ObservabilityConfiguration.from_mapping({})
    assert config == ObservabilityConfiguration()


def test_from_mapping_coerces_scalar_types() -> None:
    config = ObservabilityConfiguration.from_mapping(
        {
            "service_name": "ticket-gateway",
            "sampling_ratio": "0.25",
            "console_exporter_enabled": "false",
            "otlp_exporter_enabled": "true",
            "otlp_traces_endpoint": "http://collector:4318/v1/traces",
            "prometheus_exporter_enabled": "yes",
            "metrics_export_interval_millis": "5000",
        }
    )
    assert config.service_name == "ticket-gateway"
    assert config.sampling_ratio == 0.25
    assert config.console_exporter_enabled is False
    assert config.otlp_exporter_enabled is True
    assert config.otlp_traces_endpoint == "http://collector:4318/v1/traces"
    assert config.prometheus_exporter_enabled is True
    assert config.metrics_export_interval_millis == 5000


def test_from_mapping_preserves_otlp_headers_mapping() -> None:
    config = ObservabilityConfiguration.from_mapping(
        {"otlp_headers": {"Authorization": "Bearer token"}}
    )
    assert dict(config.otlp_headers) == {"Authorization": "Bearer token"}


def test_from_mapping_ignores_a_non_mapping_otlp_headers_value() -> None:
    config = ObservabilityConfiguration.from_mapping({"otlp_headers": "not-a-mapping"})
    assert dict(config.otlp_headers) == {}
