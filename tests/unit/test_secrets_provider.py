"""Tests: ``SecretProvider`` y ``EnvVarsProvider``."""

from __future__ import annotations

import os

import pytest

from teaf._internal.secrets import EnvVarsProvider, SecretProvider


class TestSecretProvider:
    """Tests de contrato ``SecretProvider``."""

    def test_provider_has_required_methods(self) -> None:
        """Interfaz expone `get`, `set`, `delete`, `provider_name`."""
        provider = EnvVarsProvider()
        assert hasattr(provider, "get")
        assert hasattr(provider, "set")
        assert hasattr(provider, "delete")
        assert hasattr(provider, "provider_name")

    def test_provider_name_returns_identifier(self) -> None:
        """``provider_name`` devuelve string identificador."""
        provider = EnvVarsProvider()
        assert isinstance(provider.provider_name, str)
        assert provider.provider_name == "env_vars"


class TestEnvVarsProvider:
    """Tests: ``EnvVarsProvider`` (MVP)."""

    def test_env_vars_provider_get_existing_secret(self) -> None:
        """Obtener secreto existente en ``os.environ``."""
        os.environ["TEST_SECRET"] = "secret_value_123"
        provider = EnvVarsProvider()

        result = provider.get("TEST_SECRET")

        assert result == "secret_value_123"
        del os.environ["TEST_SECRET"]

    def test_env_vars_provider_get_missing_secret_returns_none(self) -> None:
        """Obtener secreto inexistente devuelve `None`."""
        provider = EnvVarsProvider()

        result = provider.get("NONEXISTENT_SECRET_XYZ")

        assert result is None

    def test_env_vars_provider_get_missing_secret_with_default(self) -> None:
        """Obtener secreto inexistente devuelve `default`."""
        provider = EnvVarsProvider()

        result = provider.get("NONEXISTENT_SECRET_XYZ", default="fallback_value")

        assert result == "fallback_value"

    def test_env_vars_provider_set_creates_in_memory_entry(self) -> None:
        """``set()`` crea entrada en ``os.environ`` (solo sesión actual)."""
        provider = EnvVarsProvider()
        key = "TEMP_TEST_SECRET"

        provider.set(key, "temp_value_456")

        # Verificar que está en os.environ
        assert os.environ.get(key) == "temp_value_456"

        # Cleanup
        del os.environ[key]

    def test_env_vars_provider_delete_removes_from_memory(self) -> None:
        """``delete()`` remueve de ``os.environ``."""
        os.environ["TEMP_DELETE_SECRET"] = "will_be_deleted"
        provider = EnvVarsProvider()

        provider.delete("TEMP_DELETE_SECRET")

        assert os.environ.get("TEMP_DELETE_SECRET") is None

    def test_env_vars_provider_set_then_get(self) -> None:
        """Ciclo set → get funciona correctamente."""
        provider = EnvVarsProvider()
        key = "CYCLE_TEST_SECRET"
        value = "cycle_test_value_789"

        provider.set(key, value)
        result = provider.get(key)

        assert result == value

        # Cleanup
        del os.environ[key]

    def test_env_vars_provider_loads_env_file_gracefully(self) -> None:
        """Provider se inicializa sin error incluso si no hay `.env`."""
        provider = EnvVarsProvider()
        assert provider.provider_name == "env_vars"

    def test_provider_abstraction_allows_multiple_implementations(self) -> None:
        """``SecretProvider`` es interfaz que permite múltiples implementaciones."""
        provider: SecretProvider = EnvVarsProvider()

        # En v1.0.1 se podrá hacer:
        # provider = VaultProvider(url="...", token="...")
        # Sin cambiar el código que use `provider.get()`

        assert isinstance(provider, SecretProvider)
        assert provider.provider_name == "env_vars"
