"""Pruebas unitarias de backend/providers/database/base_model.py (Base, AuditMixin)."""

from __future__ import annotations

import asyncio
import uuid

from backend.providers.database.base_model import AuditMixin, Base
from backend.providers.database.engine import ConnectionParameters, DatabaseDialect, create_engine
from sqlalchemy import String
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column


class _AuditedEntity(Base, AuditMixin):
    __tablename__ = "_test_audited_entity"
    name: Mapped[str] = mapped_column(String(50))


def test_audit_mixin_declares_expected_columns() -> None:
    columns = {c.name for c in _AuditedEntity.__table__.columns}
    assert columns == {"id", "name", "created_at", "updated_at", "deleted_at"}


def test_id_is_primary_key() -> None:
    assert _AuditedEntity.__table__.c.id.primary_key is True


def test_deleted_at_is_nullable() -> None:
    assert _AuditedEntity.__table__.c.deleted_at.nullable is True


def test_created_at_and_updated_at_are_not_nullable() -> None:
    assert _AuditedEntity.__table__.c.created_at.nullable is False
    assert _AuditedEntity.__table__.c.updated_at.nullable is False


def test_table_creation_and_default_values() -> None:
    async def run() -> _AuditedEntity | None:
        engine = create_engine(DatabaseDialect.SQLITE, ConnectionParameters(database=":memory:"))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            entity = _AuditedEntity(id=uuid.uuid4(), name="demo")
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    entity = asyncio.run(run())
    assert entity is not None
    assert entity.deleted_at is None
    assert entity.created_at is not None
    assert entity.updated_at is not None
