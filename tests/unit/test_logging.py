"""Pruebas unitarias de backend/core/logging.py."""

from __future__ import annotations

import json
import logging

from teaf._internal.core.context import set_correlation_id, set_identity_context, set_trace_context
from teaf._internal.core.logging import CorrelationIdFilter, JsonFormatter, configure_logging


def _make_record(message: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )


def test_configure_logging_sets_level_and_single_console_handler() -> None:
    configure_logging(level="WARNING", log_format="console")
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1


def test_configure_logging_replaces_previous_handlers() -> None:
    configure_logging(level="INFO", log_format="console")
    configure_logging(level="INFO", log_format="console")
    assert len(logging.getLogger().handlers) == 1


def test_correlation_id_filter_injects_current_value() -> None:
    set_correlation_id("corr-abc")
    record = _make_record()
    CorrelationIdFilter().filter(record)
    assert getattr(record, "correlation_id") == "corr-abc"  # noqa: B009


def test_json_formatter_produces_expected_schema() -> None:
    set_correlation_id("corr-xyz")
    record = _make_record("evento de prueba")
    CorrelationIdFilter().filter(record)

    payload = json.loads(JsonFormatter(service_name="teaf-test").format(record))

    assert payload["service"] == "teaf-test"
    assert payload["level"] == "INFO"
    assert payload["message"] == "evento de prueba"
    assert payload["correlationId"] == "corr-xyz"
    assert payload["requestId"] == "corr-xyz"
    # Sin trace/identidad activa en este test — ver los tests de
    # enriquecimiento de contexto más abajo (Sprint 2.8, ADR-008).
    assert payload["traceId"] is None
    assert payload["spanId"] is None
    assert payload["userId"] is None
    assert payload["tenant"] is None


def test_json_formatter_includes_environment() -> None:
    record = _make_record()
    payload = json.loads(
        JsonFormatter(service_name="teaf-test", environment="staging").format(record)
    )
    assert payload["environment"] == "staging"


def test_correlation_id_filter_injects_trace_and_identity_context() -> None:
    set_trace_context(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7")
    set_identity_context(user_id="user-123", tenant_id="tenant-abc")
    record = _make_record()
    CorrelationIdFilter().filter(record)

    assert getattr(record, "trace_id") == "4bf92f3577b34da6a3ce929d0e0e4736"  # noqa: B009
    assert getattr(record, "span_id") == "00f067aa0ba902b7"  # noqa: B009
    assert getattr(record, "user_id") == "user-123"  # noqa: B009
    assert getattr(record, "tenant_id") == "tenant-abc"  # noqa: B009


def test_json_formatter_includes_real_trace_and_identity_fields_once_populated() -> None:
    set_trace_context(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7")
    set_identity_context(user_id="user-123", tenant_id="tenant-abc")
    record = _make_record()
    CorrelationIdFilter().filter(record)

    payload = json.loads(JsonFormatter(service_name="teaf-test").format(record))
    assert payload["traceId"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert payload["spanId"] == "00f067aa0ba902b7"
    assert payload["userId"] == "user-123"
    assert payload["tenant"] == "tenant-abc"

    # Aislamiento entre pruebas: no dejar contexto activo para el resto del módulo.
    set_trace_context(trace_id=None, span_id=None)
    set_identity_context(user_id=None, tenant_id=None)


def test_json_formatter_only_includes_module_and_capability_when_passed_explicitly() -> None:
    record = _make_record()
    payload = json.loads(JsonFormatter(service_name="teaf-test").format(record))
    assert "module" not in payload
    assert "capability" not in payload

    record_with_context = _make_record()
    record_with_context.module_id = "database"
    record_with_context.capability = "database.query"
    payload_with_context = json.loads(
        JsonFormatter(service_name="teaf-test").format(record_with_context)
    )
    assert payload_with_context["module"] == "database"
    assert payload_with_context["capability"] == "database.query"
