"""``DatabaseModule`` — el módulo oficial de persistencia de TEAF, sobre el Module SDK.

Primer módulo real construido enteramente heredando de ``ModuleBase``
(Sprint 2.5): sin una sola llamada directa a ``ServiceContainer`` ni a
``CapabilityRegistry`` — todo lo declara ``build_database_manifest``
(``manifest.py``) y el SDK lo registra automáticamente durante
``bootstrap()`` (``ServiceBinder``/``CapabilityBinder``).

El motor SQLAlchemy, el proveedor, la fábrica de Unit of Work y el
adaptador de salud se construyen en ``__init__`` — no en ``initialize()``
— porque ``ModuleBase.bootstrap()`` llama a ``get_manifest()`` **antes**
de ejecutar cualquier hook del ciclo de vida (ver
docs/sdk/MODULE-LIFECYCLE.md, sección 3); el manifiesto necesita esas
instancias ya construidas para declarar sus servicios. Construir el motor
es síncrono y no abre ninguna conexión real — eso ocurre en ``start()``.
"""

from __future__ import annotations

from typing import cast

from teaf._internal.modules.database.configuration import DatabaseConfiguration
from teaf._internal.modules.database.health import DatabaseHealth
from teaf._internal.modules.database.manifest import build_database_manifest
from teaf._internal.providers.database.engine import create_engine
from teaf._internal.providers.database.sqlalchemy_factory import SQLAlchemyDatabaseFactory
from teaf._internal.providers.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from teaf._internal.providers.database.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWorkFactory
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


class DatabaseModule(ModuleBase):
    """Módulo de persistencia empresarial: SQLAlchemy 2.x + Unit of Work + Repository + Alembic."""

    def __init__(self, configuration: DatabaseConfiguration | None = None) -> None:
        super().__init__()
        self.configuration = configuration or DatabaseConfiguration()
        self._engine = create_engine(
            self.configuration.dialect,
            self.configuration.connection_parameters,
            echo=self.configuration.echo,
            pool_size=self.configuration.pool_size,
            max_overflow=self.configuration.max_overflow,
        )
        self._factory = SQLAlchemyDatabaseFactory(self._engine)
        # ``DatabaseFactory.create()`` devuelve el contrato abstracto
        # ``DatabaseProvider`` por diseño (ver contracts/database.py); aquí
        # se sabe, por construcción, que ``SQLAlchemyDatabaseFactory``
        # siempre devuelve un ``SQLAlchemyDatabaseProvider`` concreto.
        self.provider = cast(SQLAlchemyDatabaseProvider, self._factory.create())
        self.uow_factory = SQLAlchemyUnitOfWorkFactory(self.provider)
        self.health = DatabaseHealth(self.provider)

    def get_manifest(self) -> ModuleManifest:
        return build_database_manifest(
            self.configuration,
            provider=self.provider,
            uow_factory=self.uow_factory,
            health=self.health,
        )

    async def start(self, context: ModuleContext) -> None:
        """Abre la conexión real y refresca la caché de salud."""
        await self.provider.connect()
        await self.health.refresh()

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info(
            "database_module_ready",
            extra={"context": {"dialect": self.configuration.dialect.value}},
        )

    async def dispose(self, context: ModuleContext) -> None:
        """Cierra el pool de conexiones — simétrico a la conexión abierta en ``start``."""
        await self.provider.disconnect()
