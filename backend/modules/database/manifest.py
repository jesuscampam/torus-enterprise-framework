"""``build_database_manifest`` — el ``ModuleManifest`` del Database Module.

Separado de ``DatabaseModule`` (``module.py``) a propósito: aquí solo se
*describe* el módulo (metadata, capacidades, servicios, configuración,
health checks) usando ``ModuleBuilder`` — nada se registra contra ningún
``Runtime`` desde este archivo, eso lo hace el SDK automáticamente durante
``ModuleBase.bootstrap()`` (ver Sprint 2.5).

Registra las seis capacidades exigidas por Sprint 2.6, ítem 9: Database,
Repository, Transactions, Migration, Connection, Health.
"""

from __future__ import annotations

from backend.contracts.database import DatabaseProvider
from backend.contracts.unit_of_work import UnitOfWork
from backend.modules.database.configuration import DatabaseConfiguration
from backend.modules.database.health import DatabaseHealth
from backend.modules.database.installer import DatabaseInstaller
from backend.providers.database.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWorkFactory
from backend.runtime.capabilities.enums import CapabilityCategory
from backend.runtime.container import Lifetime
from backend.sdk.builder import ModuleBuilder
from backend.sdk.enums import ModuleCategory
from backend.sdk.manifest import ModuleManifest


def build_database_manifest(
    configuration: DatabaseConfiguration,
    *,
    provider: DatabaseProvider,
    uow_factory: SQLAlchemyUnitOfWorkFactory,
    health: DatabaseHealth,
) -> ModuleManifest:
    """Construye el manifiesto del Database Module sobre instancias ya construidas.

    ``provider``/``uow_factory``/``health`` se construyen en
    ``DatabaseModule.__init__`` (antes de que ``bootstrap()`` llame a
    ``get_manifest()`` por primera vez) — este builder solo los declara,
    nunca los crea.
    """
    return (
        ModuleBuilder(id="database", name="database", display_name="Database")
        .with_version("1.0.0")
        .with_description(
            "Persistencia empresarial de TEAF: SQLAlchemy 2.x, Unit of Work, "
            "Repository Pattern y migraciones Alembic."
        )
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.DATABASE)
        .with_tags("sql", "persistence", configuration.dialect.value)
        .with_documentation("docs/modules/database/DATABASE.md")
        .with_runtime_compatibility(">=0.5.0")
        .with_sdk_compatibility(">=1.0.0")
        .add_capability(
            id="database",
            name="database",
            category=CapabilityCategory.DATABASE,
            description="Persistencia relacional — capacidad general del módulo.",
        )
        .add_capability(
            id="database.connection",
            name="database-connection",
            category=CapabilityCategory.DATABASE,
            description="Ciclo de vida de la conexión (connect/disconnect) a la base de datos.",
        )
        .add_capability(
            id="database.repository",
            name="database-repository",
            category=CapabilityCategory.DATABASE,
            description="Repository Pattern genérico: CRUD, paginación y filtros básicos.",
        )
        .add_capability(
            id="database.transactions",
            name="database-transactions",
            category=CapabilityCategory.DATABASE,
            description="Unit of Work transaccional sobre el Service Container.",
        )
        .add_capability(
            id="database.migration",
            name="database-migration",
            category=CapabilityCategory.DATABASE,
            description="Migraciones de esquema versionadas vía Alembic.",
        )
        .add_capability(
            id="database.health",
            name="database-health",
            category=CapabilityCategory.OBSERVABILITY,
            description="Verificación de salud de la conexión a base de datos.",
        )
        .add_configuration(
            key="dialect",
            description="sqlite | postgresql | sqlserver",
            required=False,
            default=configuration.dialect.value,
        )
        .add_configuration(
            key="database",
            description="Nombre de la base de datos o ruta del archivo",
            required=True,
        )
        .add_configuration(
            key="host", description="Host del servidor de base de datos", required=False
        )
        .add_configuration(
            key="port", description="Puerto del servidor de base de datos", required=False
        )
        .add_configuration(key="username", required=False)
        .add_configuration(key="password", required=False, sensitive=True)
        .add_configuration(key="pool_size", required=False, default=configuration.pool_size)
        .add_service(
            DatabaseProvider,
            lambda c: provider,
            lifetime=Lifetime.SINGLETON,
            description="Ciclo de vida de la conexión y fábrica de sesiones.",
            capabilities=("database.connection",),
        )
        .add_service(
            UnitOfWork,
            lambda c: uow_factory.create(),
            lifetime=Lifetime.TRANSIENT,
            description="Nueva unidad de trabajo transaccional por resolución.",
            capabilities=("database.transactions",),
        )
        .add_service(
            DatabaseInstaller,
            lambda c: DatabaseInstaller(),
            lifetime=Lifetime.SINGLETON,
            description="Orquestador de migraciones Alembic.",
            capabilities=("database.migration",),
        )
        .add_healthcheck(
            name="database.ping",
            description="SELECT 1 contra la base de datos configurada.",
            check=health.check,
        )
        .add_event("database.connected")
        .add_event("database.disconnected")
        .build()
    )
