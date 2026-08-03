# Database Module — TEAF

Documentación del Sprint 2.6 (Enterprise Persistence Foundation, v0.6.0-alpha): el primer módulo oficial de TEAF construido enteramente sobre el [Module SDK](../../sdk/SDK.md) (Sprint 2.5). Persistencia empresarial vía SQLAlchemy 2.x, Unit of Work, Repository Pattern y migraciones Alembic. Complementa — no reemplaza — [docs/standards/DATABASE-STANDARD.md](../../standards/DATABASE-STANDARD.md), que sigue siendo la fuente normativa de convenciones de modelado.

> Ninguna entidad ni tabla de negocio se define aquí. Este módulo es infraestructura pura: el "cómo" persistir, nunca el "qué" — ver sección 6.

## 1. La prueba arquitectónica de este Sprint

> Un módulo real y funcional puede construirse enteramente heredando de `ModuleBase`, sin una sola llamada directa a `ServiceContainer`/`CapabilityRegistry`.

`DatabaseModule` (`backend/modules/database/module.py`) es la primera demostración de esa promesa con código productivo detrás — no un `GreeterModule` de ejemplo. Se registra, arranca y expone sus servicios contra un `Runtime` real exactamente igual que cualquier módulo del SDK (ver `tests/integration/test_database_module_bootstrap.py`).

## 2. Arquitectura y capas

```
backend/providers/database/     # Sprint 2.2 (andamiaje) + Sprint 2.6 (implementación real)
├── engine.py                     # DatabaseDialect, ConnectionParameters, create_engine()
├── base_model.py                   # Base declarativa + AuditMixin (id/created_at/updated_at/deleted_at)
├── sqlalchemy_session.py             # SQLAlchemySessionAdapter (implementa DatabaseSession)
├── sqlalchemy_provider.py              # SQLAlchemyDatabaseProvider (implementa ConnectionManager)
├── sqlalchemy_factory.py                 # SQLAlchemyDatabaseFactory (implementa DatabaseFactory)
├── sqlalchemy_repository.py                # SQLAlchemyRepository (implementa RepositoryBase) — ver REPOSITORY.md
└── sqlalchemy_unit_of_work.py                # SQLAlchemyUnitOfWork + Factory — ver UNIT-OF-WORK.md

backend/modules/database/       # Sprint 2.6 — el módulo SDK propiamente dicho
├── configuration.py              # DatabaseConfiguration (dataclass + from_mapping)
├── health.py                       # DatabaseHealth (cache síncrona + refresh asíncrono)
├── installer.py                      # DatabaseInstaller — ver MIGRATIONS.md
├── manifest.py                         # build_database_manifest() — declara capacidades/servicios
└── module.py                             # DatabaseModule(ModuleBase)

database/migrations/            # Alembic — ver MIGRATIONS.md
alembic.ini                     # raíz del repositorio
```

**Dirección de dependencias**: `backend/modules/database/` importa de `backend/providers/database/`, nunca al revés — igual que `backend/sdk/` importa de `backend/runtime/` sin que la relación se invierta. `backend/providers/database/engine.py` no importa `backend/modules/database/` deliberadamente (recibe `ConnectionParameters` primitivos, no `DatabaseConfiguration`), para no crear un ciclo entre "el motor" y "quién lo configura".

## 3. Por qué el motor se construye en `__init__`, no en `initialize()`

`ModuleBase.bootstrap()` (Sprint 2.5) llama a `get_manifest()` **antes** de ejecutar cualquier hook del ciclo de vida — necesita el manifiesto para validar, registrar el módulo y enlazar servicios/capacidades. Como el manifiesto de este módulo declara servicios sobre instancias ya construidas (`provider`, `uow_factory`, `health`), esas instancias deben existir antes de que `bootstrap()` llame a `get_manifest()` por primera vez:

```python
class DatabaseModule(ModuleBase):
    def __init__(self, configuration: DatabaseConfiguration | None = None) -> None:
        super().__init__()
        self.configuration = configuration or DatabaseConfiguration()
        self._engine = create_engine(...)                              # síncrono, sin I/O de red
        self.provider = cast(SQLAlchemyDatabaseProvider, ...)
        self.uow_factory = SQLAlchemyUnitOfWorkFactory(self.provider)
        self.health = DatabaseHealth(self.provider)

    def get_manifest(self) -> ModuleManifest:
        return build_database_manifest(self.configuration, provider=self.provider, ...)
```

Construir el `AsyncEngine` es síncrono y no abre ninguna conexión real — eso ocurre explícitamente en `start()` (`await self.provider.connect()`), el primer hook con permiso para hacer I/O.

## 4. Uso

```python
from backend.modules.database.configuration import DatabaseConfiguration
from backend.modules.database.module import DatabaseModule
from backend.providers.database.engine import DatabaseDialect
from backend.sdk.context import ModuleContext

module = DatabaseModule(DatabaseConfiguration(dialect=DatabaseDialect.POSTGRESQL, database="teaf"))
await module.bootstrap(ModuleContext(runtime=runtime, module_id="database"))

# Servicios ya resolubles contra el Runtime:
provider = runtime.resolve_service(DatabaseProvider)   # SINGLETON
uow = runtime.resolve_service(UnitOfWork)               # TRANSIENT — nueva instancia por resolución
```

`DatabaseModule` **no** está cableado en `backend/core/application.py::create_app()` — es opt-in, igual que todo el SDK en Sprint 2.5. Auto-cablearlo introduciría una dependencia real de motor/conexión en cada test que use el `TestClient` (vía el patrón de `_lifespan` de Sprint 2.4) sin que este Sprint lo pida explícitamente. Un futuro Sprint decidirá cuándo y cómo se activa por defecto.

## 5. Las seis capacidades registradas

| Capacidad | Categoría | Qué representa |
|---|---|---|
| `database` | `DATABASE` | Persistencia relacional — capacidad general del módulo. |
| `database.connection` | `DATABASE` | Ciclo de vida `connect()`/`disconnect()`. |
| `database.repository` | `DATABASE` | Repository Pattern genérico (CRUD, paginación, filtros). |
| `database.transactions` | `DATABASE` | Unit of Work transaccional. |
| `database.migration` | `DATABASE` | Migraciones versionadas vía Alembic. |
| `database.health` | `OBSERVABILITY` | Verificación de salud de la conexión. |

Los tres servicios declarados (`DatabaseProvider` SINGLETON, `UnitOfWork` TRANSIENT, `DatabaseInstaller` SINGLETON) y las seis claves de configuración (`dialect`, `database`, `host`, `port`, `username`, `password` [sensible], `pool_size`) se listan íntegramente en `backend/modules/database/manifest.py` — ver `tests/unit/test_db_module_manifest.py` para la especificación exacta verificada.

## 6. Qué NO incluye este Sprint

Sin entidades ni tablas de negocio (la migración baseline no crea ninguna), sin autenticación/autorización, sin Azure, sin IA, sin MCP, sin Scheduler, sin driver SQL Server real (`aioodbc` no está instalado — solo la estructura del dialecto), sin Oracle. `DatabaseModule` no se registra automáticamente en `create_app()` (ver sección 4). Todo eso llega en Sprints posteriores (ver [ROADMAP.md](../../roadmap/ROADMAP.md)).

## 7. Documentos relacionados

| Documento | Contenido |
|---|---|
| [REPOSITORY.md](REPOSITORY.md) | `SQLAlchemyRepository` — API completa, filtros, paginación, soft delete. |
| [UNIT-OF-WORK.md](UNIT-OF-WORK.md) | `SQLAlchemyUnitOfWork` — límites de transacción, contrato de no-commit-implícito. |
| [MIGRATIONS.md](MIGRATIONS.md) | `DatabaseInstaller` y la estructura Alembic bajo `database/migrations/`. |
| [DATABASE-STANDARD.md](../../standards/DATABASE-STANDARD.md) | Convenciones normativas de modelado (UUID, auditoría, pooling, prácticas prohibidas). |
