# Migraciones (Alembic) — TEAF

`DatabaseInstaller` (`teaf/_internal/modules/database/installer.py`) orquesta Alembic para el Database Module. Estructura de infraestructura únicamente en este Sprint — ver [DATABASE-STANDARD.md, sección 5](../../standards/DATABASE-STANDARD.md#5-migraciones-alembic) para las reglas normativas de toda migración futura.

## 1. Estructura

```
alembic.ini                          # raíz del repositorio — script_location = database/migrations
database/migrations/
├── env.py                             # entorno async — ver sección 3
├── script.py.mako                       # plantilla de Alembic para `alembic revision`
└── versions/
    └── <hash>_baseline_infraestructura_sin_tablas_de_.py   # única revisión: upgrade()/downgrade() vacíos
```

`alembic.ini` no lleva `sqlalchemy.url` hardcodeada — se inyecta en tiempo de ejecución (ver sección 3), nunca se versiona una credencial de base de datos (ver [SECURITY-STANDARD.md](../../standards/SECURITY-STANDARD.md)).

## 2. La migración baseline

La única revisión existente en `versions/` tiene `upgrade()`/`downgrade()` vacíos (`pass`). Su propósito es exclusivamente probar el cableado end-to-end de Alembic (Alembic Config → entorno async → base de datos real → tabla `alembic_version`) — **ninguna tabla de negocio se crea**, verificado explícitamente en `tests/unit/test_db_module_installer.py::test_upgrade_to_head_creates_no_business_tables` (tras `upgrade_to_head()`, el único conjunto de tablas presente es `{"alembic_version"}`).

## 3. Por qué el entorno de Alembic es async

`target_metadata = Base.metadata` (importado de `teaf/_internal/providers/database/base_model.py`, vacío en este Sprint). `database/migrations/env.py` usa la plantilla async de Alembic (`async_engine_from_config` + `connection.run_sync(...)`) porque el motor del framework es `AsyncEngine` (SQLAlchemy 2.x asíncrono, ver [DATABASE.md](DATABASE.md)) — Alembic no tiene una forma nativa de ejecutar migraciones directamente sobre un engine asíncrono sin este puente.

La URL de conexión se resuelve en este orden:

1. Ya inyectada en `Config` por quien invoque Alembic programáticamente — así es como `DatabaseInstaller` la pasa (`config.set_main_option("sqlalchemy.url", database_url)`).
2. La variable de entorno `TEAF_DATABASE_URL`, cuando se invoca la CLI de Alembic directamente (`alembic upgrade head`) sin pasar por `DatabaseInstaller`.

## 4. `DatabaseInstaller` — API

```python
class DatabaseInstaller:
    def __init__(self, *, alembic_ini_path: Path | str = "alembic.ini") -> None: ...
    def upgrade_to_head(self, database_url: str) -> None: ...
    def downgrade(self, database_url: str, revision: str) -> None: ...
    def head_revision(self) -> str | None: ...
```

`head_revision()` solo lee el directorio `versions/` — no abre ninguna conexión a base de datos, así que no informa si esa revisión ya está aplicada en un entorno concreto (para eso, `alembic current` contra la base real).

## 5. Por qué nunca se invoca desde los hooks async de `DatabaseModule`

La API de comandos de Alembic (`command.upgrade`/`command.downgrade`) es síncrona a nivel superior, pero gestiona su propio bucle de eventos internamente (`asyncio.run(...)` dentro de `env.py`, sección 3). Invocarla desde dentro de un `Runtime` ya en ejecución — con su propio bucle `asyncio` activo durante `start()`/`ready()` — fallaría con `RuntimeError: cannot run event loop while another loop is running` (`asyncio.run()` no admite anidarse dentro de un bucle ya activo).

Por eso `DatabaseModule.start()` solo hace `provider.connect()` y `health.refresh()` — nunca llama a `DatabaseInstaller`. Aplicar migraciones es un **paso de despliegue explícito y separado**, ejecutado desde código síncrono fuera de cualquier `Runtime` en marcha:

```python
from teaf._internal.modules.database.installer import DatabaseInstaller

installer = DatabaseInstaller()
installer.upgrade_to_head("postgresql+asyncpg://user:pass@host/teaf")
```

## 6. Generar una nueva revisión

Igual que cualquier proyecto Alembic estándar, desde la raíz del repositorio:

```bash
TEAF_DATABASE_URL="sqlite+aiosqlite:///./teaf.db" alembic revision -m "descripción del cambio"
```

Toda revisión autogenerada se revisa manualmente antes de aplicarse (Alembic no detecta de forma fiable cambios de tipo, renombrados de columna, ni ciertos constraints — ver [DATABASE-STANDARD.md, sección 5](../../standards/DATABASE-STANDARD.md#5-migraciones-alembic)). Los archivos de `database/migrations/versions/` están excluidos de `ruff`/`black` (`pyproject.toml`, `extend-exclude`) porque siguen la plantilla propia de Alembic (`script.py.mako`), no las convenciones de estilo del resto del proyecto.

## 7. Qué NO incluye este Sprint

Sin tablas de negocio, sin datos semilla, sin migración automática en el arranque del `Runtime` (ver sección 5), sin integración con un pipeline de CI/CD que las aplique — eso se define cuando una aplicación real construida sobre TEAF lo necesite.
