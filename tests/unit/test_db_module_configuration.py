"""Pruebas unitarias de backend/modules/database/configuration.py (DatabaseConfiguration)."""

from __future__ import annotations

from teaf._internal.modules.database.configuration import DatabaseConfiguration
from teaf._internal.providers.database.engine import DatabaseDialect


def test_defaults_are_sqlite_in_memory() -> None:
    config = DatabaseConfiguration()
    assert config.dialect is DatabaseDialect.SQLITE
    assert config.database == ":memory:"
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.echo is False
    assert config.migrations_path == "database/migrations"


def test_connection_parameters_translates_fields() -> None:
    config = DatabaseConfiguration(
        dialect=DatabaseDialect.POSTGRESQL,
        database="teaf",
        host="db",
        port=5432,
        username="teaf",
        password="secret",
    )
    params = config.connection_parameters
    assert params.database == "teaf"
    assert params.host == "db"
    assert params.port == 5432
    assert params.username == "teaf"
    assert params.password == "secret"


def test_from_mapping_with_enum_dialect() -> None:
    config = DatabaseConfiguration.from_mapping({"dialect": DatabaseDialect.POSTGRESQL})
    assert config.dialect is DatabaseDialect.POSTGRESQL


def test_from_mapping_with_string_dialect() -> None:
    config = DatabaseConfiguration.from_mapping({"dialect": "postgresql"})
    assert config.dialect is DatabaseDialect.POSTGRESQL


def test_from_mapping_defaults_when_empty() -> None:
    config = DatabaseConfiguration.from_mapping({})
    assert config == DatabaseConfiguration()


def test_from_mapping_coerces_string_numbers() -> None:
    config = DatabaseConfiguration.from_mapping(
        {"port": "5433", "pool_size": "15", "max_overflow": "20"}
    )
    assert config.port == 5433
    assert config.pool_size == 15
    assert config.max_overflow == 20


def test_from_mapping_leaves_port_none_when_absent() -> None:
    config = DatabaseConfiguration.from_mapping({"database": "teaf"})
    assert config.port is None


def test_from_mapping_coerces_bool_variants() -> None:
    assert DatabaseConfiguration.from_mapping({"echo": "true"}).echo is True
    assert DatabaseConfiguration.from_mapping({"echo": "yes"}).echo is True
    assert DatabaseConfiguration.from_mapping({"echo": "0"}).echo is False
    assert DatabaseConfiguration.from_mapping({"echo": True}).echo is True


def test_from_mapping_optional_strings_stay_none_when_absent() -> None:
    config = DatabaseConfiguration.from_mapping({})
    assert config.host is None
    assert config.username is None
    assert config.password is None


def test_from_mapping_coerces_present_int_host_port() -> None:
    config = DatabaseConfiguration.from_mapping({"port": 5432})
    assert config.port == 5432
