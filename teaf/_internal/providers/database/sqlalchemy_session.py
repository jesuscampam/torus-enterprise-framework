"""``SQLAlchemySessionAdapter`` — implementación real de ``DatabaseSession``.

Envuelve una ``AsyncSession`` de SQLAlchemy 2.x detrás del contrato mínimo
ya definido en Sprint 2.2 (``execute``/``flush``/``close``). Expone además
``raw`` — la ``AsyncSession`` real — para uso exclusivo de otras piezas de
``backend/providers/database/`` (``SQLAlchemyRepository``,
``SQLAlchemyUnitOfWork``) que necesitan operaciones que el contrato
``DatabaseSession`` no expone (``add``, ``get``, ``scalars``, ...). Nada
fuera de este paquete debería depender de ``raw`` — el resto del framework
solo conoce ``DatabaseSession``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from teaf._internal.providers.database.session import DatabaseSession


class SQLAlchemySessionAdapter(DatabaseSession):
    """Adaptador de ``AsyncSession`` al contrato ``DatabaseSession``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def raw(self) -> AsyncSession:
        """La ``AsyncSession`` real subyacente."""
        return self._session

    async def execute(self, statement: Any) -> Any:
        return await self._session.execute(statement)

    async def flush(self) -> None:
        await self._session.flush()

    async def close(self) -> None:
        await self._session.close()
