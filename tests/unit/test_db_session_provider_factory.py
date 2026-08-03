"""Pruebas unitarias de la sesión, el proveedor y la fábrica de SQLAlchemy."""

from __future__ import annotations

import asyncio
from typing import cast

from backend.providers.database.engine import ConnectionParameters, DatabaseDialect, create_engine
from backend.providers.database.sqlalchemy_factory import SQLAlchemyDatabaseFactory
from backend.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


def _memory_engine() -> AsyncEngine:
    return create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))


def test_session_adapter_execute_flush_close() -> None:
    async def run() -> int | None:
        engine = _memory_engine()
        provider = SQLAlchemyDatabaseProvider(engine)
        session = provider.get_session()
        result = await session.execute(text("SELECT 7"))
        value = cast("int | None", result.scalar())
        await session.flush()
        await session.close()
        await engine.dispose()
        return value

    assert asyncio.run(run()) == 7


def test_session_adapter_raw_exposes_async_session() -> None:
    async def run() -> bool:
        engine = _memory_engine()
        provider = SQLAlchemyDatabaseProvider(engine)
        session = provider.get_session()
        is_async_session = isinstance(session.raw, AsyncSession)
        await session.close()
        await engine.dispose()
        return is_async_session

    assert asyncio.run(run()) is True


def test_provider_connect_is_idempotent() -> None:
    async def run() -> tuple[bool, bool]:
        engine = _memory_engine()
        provider = SQLAlchemyDatabaseProvider(engine)
        before = provider.is_connected
        await provider.connect()
        await provider.connect()  # segunda llamada no debe fallar
        after = provider.is_connected
        await provider.disconnect()
        return before, after

    before, after = asyncio.run(run())
    assert before is False
    assert after is True


def test_provider_disconnect_is_idempotent() -> None:
    async def run() -> bool:
        engine = _memory_engine()
        provider = SQLAlchemyDatabaseProvider(engine)
        await provider.connect()
        await provider.disconnect()
        await provider.disconnect()  # segunda llamada no debe fallar
        return provider.is_connected

    assert asyncio.run(run()) is False


def test_provider_health_check_true_when_reachable() -> None:
    async def run() -> bool:
        engine = _memory_engine()
        provider = SQLAlchemyDatabaseProvider(engine)
        healthy = await provider.health_check()
        await provider.disconnect()
        return healthy

    assert asyncio.run(run()) is True


def test_provider_health_check_false_when_unreachable() -> None:
    async def run() -> bool:
        engine = create_engine(
            DatabaseDialect.SQLITE,
            ConnectionParameters(database="/nonexistent-dir-teaf-test/db.sqlite3"),
        )
        provider = SQLAlchemyDatabaseProvider(engine)
        return await provider.health_check()

    assert asyncio.run(run()) is False


def test_factory_create_returns_sqlalchemy_provider() -> None:
    engine = _memory_engine()
    factory = SQLAlchemyDatabaseFactory(engine)
    provider = factory.create()
    assert isinstance(provider, SQLAlchemyDatabaseProvider)
