"""``SQLAlchemyDatabaseProvider`` — implementación real de ``DatabaseProvider``.

Primera implementación concreta de ``ConnectionManager`` (Sprint 2.2) desde
que se definió — cierra el círculo dejado abierto en ese Sprint: ya no es
solo el andamiaje de estado de conexión, sino un proveedor funcional sobre
un ``AsyncEngine`` (``backend.providers.database.engine``).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from teaf._internal.providers.database.connection_manager import ConnectionManager
from teaf._internal.providers.database.sqlalchemy_session import SQLAlchemySessionAdapter


class SQLAlchemyDatabaseProvider(ConnectionManager):
    """Proveedor de base de datos sobre un ``AsyncEngine`` ya construido."""

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__()
        self._engine = engine
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def connect(self) -> None:
        """Verifica conectividad real contra la base de datos. Idempotente."""
        if self.is_connected:
            return
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        self._mark_connected()

    async def disconnect(self) -> None:
        """Libera el pool de conexiones del motor. Idempotente."""
        if not self.is_connected:
            return
        await self._engine.dispose()
        self._mark_disconnected()

    def get_session(self) -> SQLAlchemySessionAdapter:
        """Nueva ``AsyncSession`` envuelta en ``SQLAlchemySessionAdapter``."""
        return SQLAlchemySessionAdapter(self._session_factory())

    async def health_check(self) -> bool:
        """``True`` si una conexión de prueba (``SELECT 1``) se ejecuta sin error."""
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True
