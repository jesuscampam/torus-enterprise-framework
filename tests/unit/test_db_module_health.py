"""Pruebas unitarias de backend/modules/database/health.py (DatabaseHealth)."""

from __future__ import annotations

import asyncio

from teaf._internal.modules.database.health import DatabaseHealth
from teaf._internal.providers.database.engine import (
    ConnectionParameters,
    DatabaseDialect,
    create_engine,
)
from teaf._internal.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


def test_check_starts_unknown_before_refresh() -> None:
    engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
    health = DatabaseHealth(SQLAlchemyDatabaseProvider(engine))
    assert health.check() is CapabilityHealth.UNKNOWN
    assert health.last_known is CapabilityHealth.UNKNOWN


def test_refresh_updates_to_healthy_when_reachable() -> None:
    async def scenario() -> CapabilityHealth:
        engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
        health = DatabaseHealth(SQLAlchemyDatabaseProvider(engine))
        return await health.refresh()

    result = asyncio.run(scenario())
    assert result is CapabilityHealth.HEALTHY


def test_refresh_updates_to_unhealthy_when_unreachable() -> None:
    async def scenario() -> CapabilityHealth:
        engine = create_engine(
            DatabaseDialect.SQLITE,
            ConnectionParameters(database="/nonexistent-dir-teaf-health/db.sqlite3"),
        )
        health = DatabaseHealth(SQLAlchemyDatabaseProvider(engine))
        return await health.refresh()

    result = asyncio.run(scenario())
    assert result is CapabilityHealth.UNHEALTHY


def test_check_reads_cache_without_new_io() -> None:
    async def scenario() -> tuple[CapabilityHealth, CapabilityHealth]:
        engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
        health = DatabaseHealth(SQLAlchemyDatabaseProvider(engine))
        await health.refresh()
        first = health.check()
        await engine.dispose()
        second = health.check()  # sigue leyendo la caché, no vuelve a hacer I/O
        return first, second

    first, second = asyncio.run(scenario())
    assert first is CapabilityHealth.HEALTHY
    assert second is CapabilityHealth.HEALTHY
