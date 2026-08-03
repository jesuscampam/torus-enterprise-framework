"""Pruebas unitarias de backend/providers/dependencies.py (DI de infraestructura)."""

from __future__ import annotations

import pytest
from backend.core.exceptions import InfrastructureException
from backend.providers.dependencies import (
    get_ai_provider,
    get_database_provider,
    get_security_context,
    get_storage_provider,
    get_telemetry_context,
)


def test_get_database_provider_raises_infrastructure_exception() -> None:
    with pytest.raises(InfrastructureException):
        get_database_provider()


def test_get_storage_provider_raises_infrastructure_exception() -> None:
    with pytest.raises(InfrastructureException):
        get_storage_provider()


def test_get_ai_provider_raises_infrastructure_exception() -> None:
    with pytest.raises(InfrastructureException):
        get_ai_provider()


def test_get_security_context_is_usable_today() -> None:
    assert get_security_context().is_authenticated is False


def test_get_telemetry_context_is_usable_today() -> None:
    assert get_telemetry_context().trace_id is None
