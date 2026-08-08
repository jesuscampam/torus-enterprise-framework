"""Pruebas unitarias de backend/runtime/configuration_pipeline.py."""

from __future__ import annotations

import pytest
from teaf._internal.core.exceptions import ConfigurationException
from teaf._internal.runtime.configuration_pipeline import ConfigurationPipeline


def test_validate_all_runs_every_registered_validator() -> None:
    pipeline = ConfigurationPipeline()
    calls: list[str] = []
    pipeline.register("database", lambda: calls.append("database"))
    pipeline.register("security", lambda: calls.append("security"))

    pipeline.validate_all()

    assert calls == ["database", "security"]


def test_registered_modules_lists_names() -> None:
    pipeline = ConfigurationPipeline()
    pipeline.register("database", lambda: None)

    assert pipeline.registered_modules() == ("database",)


def test_validate_all_wraps_generic_exception_as_configuration_exception() -> None:
    pipeline = ConfigurationPipeline()

    def bad_validator() -> None:
        raise ValueError("falta una variable de entorno")

    pipeline.register("database", bad_validator)

    with pytest.raises(ConfigurationException, match="database"):
        pipeline.validate_all()


def test_validate_all_propagates_configuration_exception_unchanged() -> None:
    pipeline = ConfigurationPipeline()

    def raises_configuration_exception() -> None:
        raise ConfigurationException("valor inválido")

    pipeline.register("security", raises_configuration_exception)

    with pytest.raises(ConfigurationException, match="valor inválido"):
        pipeline.validate_all()
