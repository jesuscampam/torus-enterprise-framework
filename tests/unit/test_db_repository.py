"""Pruebas unitarias de backend/providers/database/sqlalchemy_repository.py."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import TypeVar

from backend.providers.database.base_model import AuditMixin, Base
from backend.providers.database.engine import ConnectionParameters, DatabaseDialect, create_engine
from backend.providers.database.sqlalchemy_repository import SQLAlchemyRepository
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

R = TypeVar("R")


class _Widget(Base, AuditMixin):
    __tablename__ = "_test_widget"
    name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))


async def _prepared_engine() -> AsyncEngine:
    engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


def _run(coro: Callable[[], Awaitable[R]]) -> R:
    return asyncio.run(coro())


async def _seed(session: AsyncSession, *, count: int = 3) -> list[_Widget]:
    widgets = [
        _Widget(id=uuid.uuid4(), name=f"widget-{i}", category="a" if i % 2 == 0 else "b")
        for i in range(count)
    ]
    for widget in widgets:
        session.add(widget)
    await session.flush()
    await session.commit()
    return widgets


def test_add_and_get_by_id() -> None:
    async def scenario() -> _Widget | None:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            repo = SQLAlchemyRepository(session, _Widget)
            widget = _Widget(id=uuid.uuid4(), name="alpha", category="a")
            await repo.add(widget)
            await session.commit()
            return await repo.get_by_id(widget.id)

    result = _run(scenario)
    assert result is not None
    assert result.name == "alpha"


def test_get_by_id_returns_none_when_missing() -> None:
    async def scenario() -> _Widget | None:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            repo = SQLAlchemyRepository(session, _Widget)
            return await repo.get_by_id(uuid.uuid4())

    assert _run(scenario) is None


def test_list_paginated_respects_page_and_size() -> None:
    async def scenario() -> list[str]:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await _seed(session, count=5)
            repo = SQLAlchemyRepository(session, _Widget)
            page1 = await repo.list_paginated(page=1, page_size=2)
            page2 = await repo.list_paginated(page=2, page_size=2)
            return [w.name for w in page1] + [w.name for w in page2]

    names = _run(scenario)
    assert names == ["widget-0", "widget-1", "widget-2", "widget-3"]


def test_list_filtered_applies_equality_filter() -> None:
    async def scenario() -> list[str]:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await _seed(session, count=4)
            repo = SQLAlchemyRepository(session, _Widget)
            results = await repo.list_filtered(filters={"category": "a"})
            return sorted(w.name for w in results)

    assert _run(scenario) == ["widget-0", "widget-2"]


def test_count_all_and_filtered() -> None:
    async def scenario() -> tuple[int, int]:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await _seed(session, count=5)
            repo = SQLAlchemyRepository(session, _Widget)
            total = await repo.count()
            filtered = await repo.count(filters={"category": "a"})
            return total, filtered

    total, filtered = _run(scenario)
    assert total == 5
    assert filtered == 3


def test_update_persists_changes() -> None:
    async def scenario() -> str:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            widgets = await _seed(session, count=1)
            repo = SQLAlchemyRepository(session, _Widget)
            widget = widgets[0]
            widget.name = "renamed"
            await repo.update(widget)
            await session.commit()
            refreshed = await repo.get_by_id(widget.id)
            assert refreshed is not None
            return refreshed.name

    assert _run(scenario) == "renamed"


def test_delete_is_soft_and_excludes_from_queries() -> None:
    async def scenario() -> tuple[bool, int]:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            widgets = await _seed(session, count=3)
            repo = SQLAlchemyRepository(session, _Widget)
            await repo.delete(widgets[0].id)
            await session.commit()
            still_found = await repo.get_by_id(widgets[0].id)
            remaining = await repo.count()
            return still_found is None, remaining

    not_found, remaining = _run(scenario)
    assert not_found is True
    assert remaining == 2


def test_delete_unknown_id_is_idempotent() -> None:
    async def scenario() -> None:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            repo = SQLAlchemyRepository(session, _Widget)
            await repo.delete(uuid.uuid4())  # no debe lanzar

    _run(scenario)


def test_repository_never_commits_only_flushes() -> None:
    """El repositorio delimita a flush(): sin ``uow.commit()``, otra sesión no ve los cambios."""

    async def scenario() -> int:
        engine = await _prepared_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as write_session:
            repo = SQLAlchemyRepository(write_session, _Widget)
            await repo.add(_Widget(id=uuid.uuid4(), name="uncommitted", category="a"))
            # Sin commit() explícito — el repositorio nunca lo hace por su cuenta.

        async with session_factory() as read_session:
            other_repo = SQLAlchemyRepository(read_session, _Widget)
            return await other_repo.count()

    assert _run(scenario) == 0
