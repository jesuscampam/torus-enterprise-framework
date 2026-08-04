"""Pruebas unitarias de teaf/_internal/observability/models.py."""

from __future__ import annotations

from datetime import UTC, datetime

from teaf._internal.observability.models import (
    DiagnosticReport,
    HealthCheck,
    HealthReport,
    SpanKind,
    SpanStatus,
)
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


def test_span_kind_has_the_five_opentelemetry_roles() -> None:
    assert {k.value for k in SpanKind} == {"internal", "server", "client", "producer", "consumer"}


def test_span_status_has_the_three_opentelemetry_states() -> None:
    assert {s.value for s in SpanStatus} == {"unset", "ok", "error"}


def test_health_check_as_dict_never_includes_the_callable() -> None:
    check = HealthCheck(name="db.ping", check=lambda: CapabilityHealth.HEALTHY, description="ok")
    payload = check.as_dict()
    assert payload == {"name": "db.ping", "description": "ok", "critical": True}
    assert "check" not in payload


def test_health_check_check_may_be_none() -> None:
    check = HealthCheck(name="unregistered", check=None)
    assert check.check is None


def test_health_report_as_dict_serializes_enum_values() -> None:
    report = HealthReport(
        overall=CapabilityHealth.DEGRADED,
        checks={"a": CapabilityHealth.HEALTHY, "b": CapabilityHealth.DEGRADED},
    )
    assert report.as_dict() == {
        "status": "degraded",
        "checks": {"a": "healthy", "b": "degraded"},
    }


def test_diagnostic_report_as_dict_wraps_runtime_and_health_without_duplicating_fields() -> None:
    generated_at = datetime(2026, 8, 4, tzinfo=UTC)
    health = HealthReport(overall=CapabilityHealth.HEALTHY, checks={})
    report = DiagnosticReport(
        generated_at=generated_at, runtime={"runtimeId": "abc"}, health=health
    )
    payload = report.as_dict()
    assert payload["generatedAt"] == generated_at.isoformat()
    assert payload["runtime"] == {"runtimeId": "abc"}
    assert payload["health"] == {"status": "healthy", "checks": {}}
