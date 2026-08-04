"""``SQLAlchemyUnitOfWork`` — implementación real de ``UnitOfWork``.

``__aexit__`` revierte automáticamente si el bloque ``async with`` termina
por excepción — nunca hace commit implícito (ver el contrato en
``backend/contracts/unit_of_work.py``): confirmar la transacción es
siempre una llamada explícita a ``commit()``, responsabilidad de
``services/`` (ver [DATABASE-STANDARD.md, sección 7](../../../docs/standards/DATABASE-STANDARD.md)).

``SQLAlchemyUnitOfWorkFactory`` es la pieza que se registra como servicio
``TRANSIENT`` en el ``ServiceContainer`` (ver ``backend/modules/database/manifest.py``)
— cada resolución produce un ``SQLAlchemyUnitOfWork`` nuevo, sobre una
sesión fresca, nunca una compartida entre llamadas.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from teaf._internal.contracts.unit_of_work import UnitOfWork
from teaf._internal.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider


class SQLAlchemyUnitOfWork(UnitOfWork):
    """Delimita una transacción sobre una ``AsyncSession``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """La ``AsyncSession`` de esta unidad de trabajo — para construir repositorios."""
        return self._session

    async def __aenter__(self) -> SQLAlchemyUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


class SQLAlchemyUnitOfWorkFactory:
    """Construye un ``SQLAlchemyUnitOfWork`` nuevo por invocación, sobre una sesión fresca."""

    def __init__(self, provider: SQLAlchemyDatabaseProvider) -> None:
        self._provider = provider

    def create(self) -> SQLAlchemyUnitOfWork:
        """Nuevo ``SQLAlchemyUnitOfWork`` — nunca reutiliza una sesión de una unidad anterior."""
        session_adapter = self._provider.get_session()
        return SQLAlchemyUnitOfWork(session_adapter.raw)
