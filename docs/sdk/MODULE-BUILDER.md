# Module Builder — TEAF

`ModuleBuilder` (`teaf/_internal/sdk/builder.py`) es la forma recomendada — y única probada — de construir un `ModuleManifest`: un builder fluido donde cada `with_*`/`add_*` devuelve `self`. Ver visión general en [SDK.md](SDK.md).

## 1. API completa

```python
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.runtime.container import Lifetime

manifest = (
    ModuleBuilder(id="database", name="database", display_name="Database")
    .with_version("1.0.0")
    .with_description("Acceso a PostgreSQL")
    .with_author("TEAF Team")
    .with_license("MIT")
    .with_category(ModuleCategory.DATABASE)
    .with_tags("sql", "postgres")
    .with_documentation("docs/database/DATABASE.md")
    .with_runtime_compatibility(">=0.5.0")
    .with_sdk_compatibility(">=1.0.0")
    .as_experimental()          # opcional
    .as_deprecated()            # opcional
    .add_service(DatabaseProvider, lambda c: PostgresProvider(), lifetime=Lifetime.SINGLETON)
    .add_capability(id="database.query", name="database-query")
    .add_dependency(module_id="security", version_constraint=">=1.0.0", optional=False)
    .add_configuration(key="DATABASE_URL", required=True, sensitive=True)
    .add_healthcheck(name="database.ping", description="Verifica la conexión")
    .add_event("database.connected")
    .build()
)
```

| Método | Sección del manifiesto |
|---|---|
| `with_version`, `with_description`, `with_author`, `with_category`, `with_tags`, `with_documentation`, `as_experimental`, `as_deprecated` | Metadata (`ModuleDescriptor`) |
| `with_license` | `ModuleManifest.license` |
| `add_service` | `ModuleService` |
| `add_capability` | `ModuleCapability` |
| `add_dependency` | `ModuleDependency` |
| `add_configuration` | `ModuleConfiguration` |
| `add_healthcheck` | `ModuleHealth` |
| `add_event` | `ModuleManifest.events` |
| `with_runtime_compatibility`, `with_sdk_compatibility` | Packaging |
| `build()` | Construye el `ModuleManifest` final |

`display_name` es opcional en el constructor — si se omite, toma el valor de `name`; `with_display_name(...)` lo sobrescribe explícitamente en cualquier momento antes de `build()`.

## 2. Uso típico dentro de `ModuleBase`

El builder normalmente no se usa suelto — vive dentro de `get_manifest()`:

```python
class DatabaseModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="database", name="database", display_name="Database")
            .with_category(ModuleCategory.DATABASE)
            .add_service(DatabaseProvider, lambda c: PostgresProvider())
            .build()
        )
```

Cada llamada a `get_manifest()` construye un manifiesto **nuevo** — el builder no mantiene estado entre llamadas ni se reutiliza la misma instancia. Esto es intencional: `get_manifest()` debe ser puro (ver [SDK.md, sección 5](SDK.md#5-buenas-prácticas)), así que reconstruir desde cero en cada llamada es lo correcto, no un desperdicio a evitar.

## 3. Ejemplo por cada una de las 7 categorías

`ModuleCategory` (`teaf/_internal/sdk/enums.py`) tiene 7 valores, cada uno con una plantilla asociada en `MODULE_TEMPLATES` (ver `templates.py` y `ModuleScaffolder` en [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md)):

| Categoría | Ejemplo de capacidad sugerida |
|---|---|
| `GENERIC` | — (sin sugerencias, punto de partida mínimo) |
| `DATABASE` | `database.query`, `database.migrate` |
| `SECURITY` | `security.authenticate`, `security.authorize` |
| `STORAGE` | `storage.upload`, `storage.download` |
| `INTEGRATION` | `integration.sync` |
| `AI` | `ai.generate-text`, `ai.generate-embedding` |
| `MCP` | `mcp.expose-tool` |

```python
ModuleBuilder(id="ai", name="ai", display_name="AI").with_category(ModuleCategory.AI).build()
```

## 4. Buenas prácticas

- **Construye el manifiesto completo en una sola expresión encadenada** — no guardes el builder en una variable intermedia y lo mutes en varios pasos; rompe la inmutabilidad que `build()` garantiza al final.
- **Valida siempre lo que produce el builder** antes de registrarlo — `ModuleBuilder` no valida nada por sí mismo (ni siquiera formatos básicos); esa responsabilidad es de `ModuleValidator`, invocado automáticamente por `ModuleBase.bootstrap()`.
- **No captures estado mutable en las lambdas de `add_service`** — la factory recibe el `ServiceContainer` y debe poder llamarse más de una vez (`TRANSIENT`) sin efectos acumulativos.
- **Usa `add_dependency(..., optional=True)` para integraciones opcionales** — un módulo que funciona con o sin otro presente debería declararlo así, no omitir la dependencia por completo (perdiendo la documentación de la relación).
