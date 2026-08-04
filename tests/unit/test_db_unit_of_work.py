"""Pruebas unitarias de backend/providers/database/sqlalchemy_unit_of_work.py."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from teaf._internal.providers.database.base_model import AuditMixin, Base
from teaf._internal.providers.database.engine import (
    ConnectionParameters,
    DatabaseDialect,
    create_engine,
)
from teaf._internal.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from teaf._internal.providers.database.sqlalchemy_repository import SQLAlchemyRepository
from teaf._internal.providers.database.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
    SQLAlchemyUnitOfWorkFactory,
)


class _Ledger(Base, AuditMixin):
    __tablename__ = "_test_ledger"
    label: Mapped[str] = mapped_column(String(50))


async def _prepared_provider() -> SQLAlchemyDatabaseProvider:
    engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return SQLAlchemyDatabaseProvider(engine)


def test_uow_aenter_returns_self() -> None:
    async def scenario() -> bool:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)
        uow = factory.create()
        async with uow as entered:
            return entered is uow

    assert asyncio.run(scenario()) is True


def test_uow_commit_persists_changes() -> None:
    async def scenario() -> int:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            await repo.add(_Ledger(id=uuid.uuid4(), label="committed"))
            await uow.commit()

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            return await repo.count()

    assert asyncio.run(scenario()) == 1


def test_uow_rolls_back_on_exception() -> None:
    async def scenario() -> int:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)

        try:
            async with factory.create() as uow:
                repo = SQLAlchemyRepository(uow.session, _Ledger)
                await repo.add(_Ledger(id=uuid.uuid4(), label="doomed"))
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            return await repo.count()

    assert asyncio.run(scenario()) == 0


def test_uow_never_auto_commits_on_clean_exit() -> None:
    """Salir del bloque sin excepción y sin llamar commit() no persiste nada."""

    async def scenario() -> int:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            await repo.add(_Ledger(id=uuid.uuid4(), label="never-committed"))
            # Sin uow.commit() — el contrato prohíbe el commit implícito.

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            return await repo.count()

    assert asyncio.run(scenario()) == 0


def test_uow_explicit_rollback() -> None:
    async def scenario() -> int:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            await repo.add(_Ledger(id=uuid.uuid4(), label="explicit-rollback"))
            await uow.rollback()

        async with factory.create() as uow:
            repo = SQLAlchemyRepository(uow.session, _Ledger)
            return await repo.count()

    assert asyncio.run(scenario()) == 0


def test_factory_creates_independent_units_of_work() -> None:
    async def scenario() -> bool:
        provider = await _prepared_provider()
        factory = SQLAlchemyUnitOfWorkFactory(provider)
        uow1 = factory.create()
        uow2 = factory.create()
        return uow1 is not uow2 and uow1.session is not uow2.session

    assert asyncio.run(scenario()) is True


def test_uow_session_property_returns_async_session() -> None:
    async def scenario() -> SQLAlchemyUnitOfWork:
        provider = await _prepared_provider()
        return SQLAlchemyUnitOfWorkFactory(provider).create()

    uow = asyncio.run(scenario())
    assert uow.session is not None
