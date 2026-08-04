"""Pruebas unitarias de backend/core/logging.py."""

from __future__ import annotations

import json
import logging

from teaf._internal.core.context import set_correlation_id
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
    # Reservado para OpenTelemetry — todavía no implementado (Sprint 2.1).
    assert payload["traceId"] is None
