"""``SQLAlchemyDatabaseFactory`` — implementación real de ``DatabaseFactory``.

Construye un ``SQLAlchemyDatabaseProvider`` a partir de un ``AsyncEngine``
ya ensamblado (``backend.providers.database.engine.create_engine``) — el
factory en sí no conoce dialectos ni cadenas de conexión, eso ya se
resolvió al construir el motor.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.contracts.database import DatabaseProvider
from backend.providers.database.factory import DatabaseFactory
from backend.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider


class SQLAlchemyDatabaseFactory(DatabaseFactory):
    """Construye ``SQLAlchemyDatabaseProvider`` sobre un ``AsyncEngine`` dado."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    def create(self) -> DatabaseProvider:
        return SQLAlchemyDatabaseProvider(self._engine)
