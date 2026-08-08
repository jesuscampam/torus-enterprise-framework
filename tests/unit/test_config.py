"""Pruebas unitarias de backend/config/ (Environment y Settings)."""

from __future__ import annotations

import pytest
from teaf._internal.config.environment import Environment, get_environment
from teaf._internal.config.settings import ProductionSettings, TestingSettings, get_settings
from teaf._internal.core.exceptions import ConfigurationException


def test_get_environment_defaults_to_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert get_environment() == Environment.DEVELOPMENT


def test_get_environment_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert get_environment() == Environment.STAGING


def test_get_environment_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    assert get_environment() == Environment.PRODUCTION


def test_get_environment_rejects_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "not-a-real-environment")
    with pytest.raises(ConfigurationException):
        get_environment()


def test_get_settings_selects_class_by_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert isinstance(settings, ProductionSettings)
        assert settings.debug is False
        assert settings.docs_enabled is False
    finally:
        get_settings.cache_clear()


def test_get_settings_is_cached_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_testing_settings_defaults() -> None:
    settings = TestingSettings()
    assert settings.environment == Environment.TESTING
    assert settings.debug is True
