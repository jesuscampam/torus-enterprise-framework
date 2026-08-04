"""Pruebas unitarias de backend/providers/database/engine.py."""

from __future__ import annotations

import asyncio
from typing import cast

from sqlalchemy import text
from sqlalchemy.pool import QueuePool
from teaf._internal.providers.database.engine import (
    ConnectionParameters,
    DatabaseDialect,
    build_database_url,
    create_engine,
    is_in_memory_sqlite,
)


def test_build_url_sqlite_memory() -> None:
    url = build_database_url(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
    assert url == "sqlite+aiosqlite:///:memory:"


def test_build_url_sqlite_file_path() -> None:
    url = build_database_url(DatabaseDialect.SQLITE, ConnectionParameters(database="/tmp/x.db"))
    assert url == "sqlite+aiosqlite:////tmp/x.db"


def test_build_url_postgresql_with_credentials() -> None:
    params = ConnectionParameters(
        database="teaf", host="db", port=5432, username="teaf", password="secret"
    )
    url = build_database_url(DatabaseDialect.POSTGRESQL, params)
    assert url == "postgresql+asyncpg://teaf:secret@db:5432/teaf"


def test_build_url_postgresql_without_password() -> None:
    params = ConnectionParameters(database="teaf", host="db", username="teaf")
    url = build_database_url(DatabaseDialect.POSTGRESQL, params)
    assert url == "postgresql+asyncpg://teaf@db/teaf"


def test_build_url_postgresql_defaults_host_to_localhost() -> None:
    params = ConnectionParameters(database="teaf")
    url = build_database_url(DatabaseDialect.POSTGRESQL, params)
    assert url == "postgresql+asyncpg://localhost/teaf"


def test_build_url_sqlserver_structure_prepared() -> None:
    params = ConnectionParameters(database="teaf", host="sql", port=1433, username="sa")
    url = build_database_url(DatabaseDialect.SQLSERVER, params)
    assert url == "mssql+aioodbc://sa@sql:1433/teaf"


def test_is_in_memory_sqlite_true_for_memory_and_empty() -> None:
    assert is_in_memory_sqlite(ConnectionParameters(database=":memory:")) is True
    assert is_in_memory_sqlite(ConnectionParameters(database="")) is True


def test_is_in_memory_sqlite_false_for_file_path() -> None:
    assert is_in_memory_sqlite(ConnectionParameters(database="/tmp/x.db")) is False


def test_create_engine_sqlite_memory_executes_query() -> None:
    async def run() -> int | None:
        engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return result.scalar()

    assert asyncio.run(run()) == 1


def test_create_engine_postgresql_uses_pool_kwargs() -> None:
    engine = create_engine(
        DatabaseDialect.POSTGRESQL,
        ConnectionParameters(database="teaf", host="db"),
        pool_size=7,
        max_overflow=3,
    )
    assert cast(QueuePool, engine.pool).size() == 7
