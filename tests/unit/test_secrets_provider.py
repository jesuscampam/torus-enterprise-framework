"""Tests: ``SecretProvider`` y ``EnvVarsProvider``.

**Funciones sueltas, no clases.** ``pyproject.toml`` fija ``python_classes = []``
para que ``TestingSettings`` no se confunda con una clase de prueba, así que
pytest **ignora en silencio** cualquier test escrito dentro de una clase. Estas
pruebas nacieron así en Sprint 3.2-light y por eso nunca llegaron a ejecutarse;
convertirlas fue lo que destapó el fallo de logging que cubre la última.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

import pytest
from teaf._internal.secrets import EnvVarsProvider, SecretProvider


@pytest.fixture
def provider() -> EnvVarsProvider:
    """Proveedor recién construido."""
    return EnvVarsProvider()


@pytest.fixture
def temp_env_key() -> Iterator[str]:
    """Nombre de variable de entorno que se limpia al terminar la prueba.

    La limpieza va en la fixture y no al final del test: si una aserción falla
    antes, el ``del`` nunca se ejecutaría y la variable se filtraría a las
    pruebas siguientes.
    """
    key = "TEAF_TEMP_TEST_SECRET"
    yield key
    os.environ.pop(key, None)


# --- Contrato de SecretProvider -------------------------------------------


def test_provider_exposes_the_contract_methods(provider: EnvVarsProvider) -> None:
    """La interfaz expone ``get``, ``set``, ``delete`` y ``provider_name``."""
    assert hasattr(provider, "get")
    assert hasattr(provider, "set")
    assert hasattr(provider, "delete")
    assert hasattr(provider, "provider_name")


def test_provider_name_returns_identifier(provider: EnvVarsProvider) -> None:
    """``provider_name`` devuelve el identificador del proveedor."""
    assert provider.provider_name == "env_vars"


def test_provider_abstraction_allows_multiple_implementations(
    provider: EnvVarsProvider,
) -> None:
    """``SecretProvider`` es la interfaz que permitirá cambiar a Vault sin tocar
    el código que consume ``provider.get()``."""
    as_contract: SecretProvider = provider

    assert isinstance(as_contract, SecretProvider)


# --- Lectura ---------------------------------------------------------------


def test_get_returns_existing_secret(provider: EnvVarsProvider, temp_env_key: str) -> None:
    """Un secreto presente en ``os.environ`` se devuelve tal cual."""
    os.environ[temp_env_key] = "secret_value_123"

    assert provider.get(temp_env_key) == "secret_value_123"


def test_get_returns_none_for_missing_secret(provider: EnvVarsProvider) -> None:
    """Un secreto inexistente devuelve ``None``."""
    assert provider.get("TEAF_NONEXISTENT_SECRET_XYZ") is None


def test_get_returns_default_for_missing_secret(provider: EnvVarsProvider) -> None:
    """Un secreto inexistente devuelve el ``default`` recibido."""
    assert provider.get("TEAF_NONEXISTENT_SECRET_XYZ", default="fallback") == "fallback"


# --- Escritura y borrado ---------------------------------------------------


def test_set_creates_in_memory_entry(provider: EnvVarsProvider, temp_env_key: str) -> None:
    """``set()`` escribe en ``os.environ`` (solo para la sesión en curso)."""
    provider.set(temp_env_key, "temp_value_456")

    assert os.environ.get(temp_env_key) == "temp_value_456"


def test_delete_removes_from_memory(provider: EnvVarsProvider, temp_env_key: str) -> None:
    """``delete()`` retira la variable de ``os.environ``."""
    os.environ[temp_env_key] = "will_be_deleted"

    provider.delete(temp_env_key)

    assert os.environ.get(temp_env_key) is None


def test_delete_is_tolerant_with_a_missing_key(provider: EnvVarsProvider) -> None:
    """Borrar algo que no existe no lanza."""
    provider.delete("TEAF_NONEXISTENT_SECRET_XYZ")


def test_set_then_get_round_trip(provider: EnvVarsProvider, temp_env_key: str) -> None:
    """El ciclo ``set`` → ``get`` devuelve el valor escrito."""
    provider.set(temp_env_key, "cycle_test_value_789")

    assert provider.get(temp_env_key) == "cycle_test_value_789"


def test_provider_initialises_without_an_env_file(provider: EnvVarsProvider) -> None:
    """El proveedor arranca aunque no haya ``.env`` en el directorio."""
    assert provider.provider_name == "env_vars"


# --- Regresión -------------------------------------------------------------


def test_set_and_delete_work_with_debug_logging_enabled(
    provider: EnvVarsProvider, temp_env_key: str, caplog: pytest.LogCaptureFixture
) -> None:
    """``set``/``delete`` no revientan con el nivel DEBUG activo.

    Los campos del log viajaban como kwargs sueltos
    (``logger.debug(msg, key=..., provider=...)``). ``Logger.debug`` los admite
    en su ``**kwargs``, pero solo se los pasa a ``Logger._log`` **si el nivel
    está habilitado**: por eso el ``TypeError`` aparecía únicamente con DEBUG
    encendido —el nivel por defecto en desarrollo— y quedaba invisible en
    cualquier prueba con el logging apagado.
    """
    with caplog.at_level(logging.DEBUG):
        provider.set(temp_env_key, "valor-secreto")
        provider.delete(temp_env_key)

    assert provider.get(temp_env_key) is None
    assert any(record.message == "secret_set_in_memory" for record in caplog.records)
    # Se registra el nombre de la clave, nunca el valor (SECURITY-STANDARD.md).
    assert not any("valor-secreto" in record.getMessage() for record in caplog.records)
