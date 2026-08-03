"""``SQLAlchemyRepository`` — implementación funcional de ``RepositoryBase``.

CRUD genérico, paginación y filtros básicos sobre cualquier modelo que
herede de ``Base``+``AuditMixin`` (``backend.providers.database.base_model``).
Ningún método hace ``commit()`` — solo ``flush()`` — la transacción la
delimita ``SQLAlchemyUnitOfWork`` (ver ``sqlalchemy_unit_of_work.py``),
igual que exige [DATABASE-STANDARD.md, sección 7](../../../docs/standards/DATABASE-STANDARD.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.providers.database.base_model import AuditMixin
from backend.providers.database.repository_base import RepositoryBase
from backend.providers.database.sqlalchemy_session import SQLAlchemySessionAdapter

#: A diferencia del ``T`` sin cota de ``contracts/repository.py`` (deliberado
#: allí para no acoplar ``contracts/`` a ningún ORM), aquí sí se acota a
#: ``AuditMixin`` — esta clase vive en ``providers/``, ya sabe que opera
#: sobre modelos SQLAlchemy con columnas de auditoría.
TModel = TypeVar("TModel", bound=AuditMixin)

#: Preserva el tipo concreto de ``Select`` (``Select[tuple[TModel]]`` o
#: ``Select[tuple[int]]`` para ``count``) a través de ``_apply_filters``.
S = TypeVar("S", bound=Select[Any])


class SQLAlchemyRepository(RepositoryBase[TModel], Generic[TModel]):
    """Repositorio genérico sobre un modelo SQLAlchemy mapeado (``model``).

    ``session`` es una ``AsyncSession`` real — normalmente
    ``unit_of_work.session`` (``SQLAlchemyUnitOfWork``) o
    ``provider.get_session().raw`` — nunca una nueva por su cuenta; el
    repositorio nunca decide su propia frontera transaccional.
    """

    def __init__(self, session: AsyncSession, model: type[TModel]) -> None:
        super().__init__(SQLAlchemySessionAdapter(session))
        self._model = model
        self._raw_session = session

    async def get_by_id(self, entity_id: UUID) -> TModel | None:
        statement = select(self._model).where(
            self._model.id == entity_id, self._model.deleted_at.is_(None)
        )
        result = await self._raw_session.execute(statement)
        return result.scalar_one_or_none()

    async def list_paginated(self, *, page: int, page_size: int) -> list[TModel]:
        return await self.list_filtered(page=page, page_size=page_size)

    async def list_filtered(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Mapping[str, object] | None = None,
    ) -> list[TModel]:
        """Como ``list_paginated``, con filtros de igualdad opcionales por columna.

        ``filters`` es un mapa ``{nombre_de_columna: valor}`` — filtros
        "básicos" de igualdad, sin operadores de comparación ni joins.
        """
        statement = self._apply_filters(select(self._model), filters)
        statement = (
            statement.order_by(self._model.created_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._raw_session.execute(statement)
        return list(result.scalars().all())

    async def count(self, *, filters: Mapping[str, object] | None = None) -> int:
        """Número total de entidades activas que cumplen ``filters``."""
        statement = self._apply_filters(select(func.count()).select_from(self._model), filters)
        result = await self._raw_session.execute(statement)
        return int(result.scalar_one())

    async def add(self, entity: TModel) -> TModel:
        self._raw_session.add(entity)
        await self._raw_session.flush()
        return entity

    async def update(self, entity: TModel) -> TModel:
        await self._raw_session.flush()
        return entity

    async def delete(self, entity_id: UUID) -> None:
        """Baja lógica (``deleted_at``) — no elimina físicamente. Idempotente."""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return
        entity.deleted_at = datetime.now(UTC)
        await self._raw_session.flush()

    def _apply_filters(self, statement: S, filters: Mapping[str, object] | None) -> S:
        statement = statement.where(self._model.deleted_at.is_(None))
        for column_name, value in (filters or {}).items():
            statement = statement.where(getattr(self._model, column_name) == value)
        return statement
