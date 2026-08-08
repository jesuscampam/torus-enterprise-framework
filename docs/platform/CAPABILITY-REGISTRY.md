# Capability Registry — TEAF

El **Capability Model** es el vocabulario que usa TEAF para describir "qué puede hacer" una instancia en ejecución — más fino que un módulo (`ModuleRegistry`, Sprint 2.2) y más operativo que un feature flag (ver [SELF-DESCRIBING-RUNTIME.md](SELF-DESCRIBING-RUNTIME.md)). Vive en `teaf/_internal/runtime/capabilities/`. Ver visión general en [PLATFORM-INTELLIGENCE.md](PLATFORM-INTELLIGENCE.md).

> Ninguna capacidad real se registra en este Sprint (ver Sprint 2.4, "NO IMPLEMENTAR") — solo la infraestructura para hacerlo. La primera capacidad real la registrará el módulo correspondiente cuando deje de ser `contracts_only`.

## 1. `CapabilityMetadata` — los datos

`CapabilityMetadata` (`metadata.py`) es un `dataclass` inmutable (`frozen=True, slots=True`) con 17 campos descriptivos:

| Campo | Tipo | Descripción |
|---|---|---|
| `id`, `name`, `display_name` | `str` | Identidad de la capacidad (`id` es el identificador estable, p. ej. `"database.query"`). |
| `description`, `version` | `str` | Descripción libre y versión semántica. |
| `category` | `CapabilityCategory` | Ver sección 2. |
| `provider`, `module` | `str \| None` | Quién la implementa y a qué módulo pertenece. |
| `status` | `CapabilityStatus` | `REGISTERED` / `ACTIVE` / `DISABLED` / `DEPRECATED`. |
| `experimental`, `deprecated` | `bool` | Banderas informativas. |
| `owner` | `str \| None` | Equipo/persona responsable. |
| `tags` | `tuple[str, ...]` | Búsqueda libre (ver `CapabilityRegistry.search`). |
| `documentation` | `str \| None` | Ruta o URL a la documentación de la capacidad. |
| `permissions_required`, `configuration_required` | `tuple[str, ...]` | Requisitos declarativos, sin validación en este Sprint. |
| `dependencies` | `tuple[str, ...]` | IDs de otras capacidades de las que depende. |
| `health` | `CapabilityHealth` | Ver sección 2. |
| `metrics` | `Mapping[str, float]` | Sin uso en este Sprint — listo para observabilidad futura. |
| `created_at`, `updated_at` | `datetime` | UTC, asignados automáticamente. |

`CapabilityMetadata.as_dict()` produce la forma JSON (`camelCase`) expuesta por la Runtime API. `Capability` (también en `metadata.py`) envuelve la metadata más un `health_check: Callable[[], CapabilityHealth] | None` opcional — sin uso en este Sprint, preparado para que un Sprint futuro conecte verificaciones de salud en vivo.

## 2. Enumeraciones

**`CapabilityCategory`** (`enums.py`) — 13 valores: `SYSTEM`, `PLATFORM`, `DATABASE`, `SECURITY`, `STORAGE`, `AI`, `MCP`, `NOTIFICATION`, `SCHEDULER`, `OBSERVABILITY`, `INTEGRATION`, `UTILITY`, `CUSTOM` (por defecto).

**`CapabilityStatus`**: `REGISTERED` (por defecto) → `ACTIVE` → `DISABLED` / `DEPRECATED`.

**`CapabilityHealth`**: `UNKNOWN` (por defecto), `HEALTHY`, `DEGRADED`, `UNHEALTHY` — declarativo, sin verificación automática en este Sprint.

## 3. `CapabilityBuilder` — construcción fluida

```python
from teaf._internal.runtime.capabilities.builder import CapabilityBuilder
from teaf._internal.runtime.capabilities.enums import CapabilityCategory

capability = (
    CapabilityBuilder(id="database.query", name="database-query")
    .with_display_name("Consulta de base de datos")
    .with_category(CapabilityCategory.DATABASE)
    .with_module("database")
    .with_tags("sql", "postgres")
    .build()
)
```

Cada `with_*`/`as_*` devuelve `self` para encadenar; `build()` construye la `CapabilityMetadata` final y la envuelve en `Capability`. El builder usa atributos internos explícitamente tipados (no `**kwargs`) — evita `# type: ignore` bajo `mypy --strict`.

## 4. `CapabilityRegistry` — el inventario

```python
from teaf._internal.runtime.capabilities.registry import CapabilityRegistry

registry = CapabilityRegistry()
registry.register(capability)                 # CapabilityAlreadyRegisteredException si el id ya existe
registry.exists("database.query")              # bool
registry.find("database.query")                 # Capability | None
registry.describe("database.query")              # Capability — CapabilityNotFoundException si no existe
registry.list(category=CapabilityCategory.DATABASE)  # filtrado opcional
registry.search("sql")                           # substring en id/name/display_name/tags
registry.unregister("database.query")             # CapabilityNotFoundException si no existe
```

En producción, **usa siempre `Runtime.register_capability()`/`Runtime.remove_capability()`** (ver [PLATFORM-INTELLIGENCE.md, sección 5](PLATFORM-INTELLIGENCE.md#5-buenas-prácticas-para-extender-platform-intelligence)) en vez del registro directo — son los que publican `capability.registered`/`capability.removed` en el `EventBus`. Llamar al registro directamente (como en pruebas unitarias) es válido y no publica eventos.

## 5. Preparación para MCP: `CapabilityProviderRegistry`

Un futuro servidor MCP necesitará descubrir, de una sola llamada, todas las capacidades que expone el framework — sin conocer de antemano cada módulo. `CapabilityProviderRegistry` (`provider_registry.py`) resuelve ese caso de uso **sin implementar MCP**:

```python
from teaf._internal.runtime.capabilities.provider_registry import CapabilityProviderRegistry

provider_registry = CapabilityProviderRegistry()
provider_registry.register("database", database_capability_provider)
provider_registry.register("security", security_capability_provider)

all_capabilities = provider_registry.discover_all_capabilities()  # agrega get_capabilities() de todos
```

**Decisión de diseño clave**: `CapabilityProviderRegistry` no importa `teaf/_internal/contracts/` (donde vive el contrato real `CapabilityProvider`, ver `teaf/_internal/contracts/capability_provider.py`) — usa un `typing.Protocol` estructural local, `CapabilityProviderLike`, con la misma forma (`get_capabilities() -> Sequence[Any]`). Cualquier implementación real de `CapabilityProvider` encaja aquí por *duck typing*, sin herencia ni import cruzado — así `teaf/_internal/runtime/` conserva la regla "nunca depende de `contracts/` ni `providers/`" (ver [RUNTIME.md](../runtime/RUNTIME.md)) incluso al prepararse para un futuro consumidor externo.

`Runtime` expone esto como `runtime.capability_provider_registry`, compuesto junto al resto de piezas del Runtime.

## 6. Preparación para IA: los contratos

Dos contratos nuevos en `teaf/_internal/contracts/`, sin implementación real:

- **`CapabilityProvider`** (`capability_provider.py`): `get_capabilities() -> Sequence[Any]` — lo que un módulo futuro implementa para anunciarse ante `CapabilityProviderRegistry`.
- **`FrameworkKnowledgeProvider`** (`framework_knowledge.py`): `async describe_framework() -> Mapping[str, object]` y `async answer_question(question: str) -> str` — la forma que tendrá, en un Sprint futuro, un componente de IA capaz de responder preguntas sobre TEAF apoyándose en su propia introspección.

Ambos siguen el mismo patrón que el resto de `teaf/_internal/contracts/`: `ABC` puro, sin imports de `teaf/_internal/`, cero implementación.

## 7. Ejemplo end-to-end

```python
from teaf._internal.runtime.capabilities.builder import CapabilityBuilder
from teaf._internal.runtime.capabilities.enums import CapabilityCategory

capability = (
    CapabilityBuilder(id="ai.generate-text", name="ai-generate-text")
    .with_category(CapabilityCategory.AI)
    .with_module("ai")
    .build()
)

runtime.register_capability(capability)     # publica "capability.registered"
runtime.capability_registry.exists("ai.generate-text")  # True
runtime.remove_capability("ai.generate-text")  # publica "capability.removed"
```

## 8. Buenas prácticas

- **Un `id` de capacidad es para siempre**: una vez publicado (y consumido por `GET /runtime/capabilities` o un futuro MCP), cambiarlo rompe a cualquier consumidor externo. Prefiere deprecar (`CapabilityStatus.DEPRECATED`) a renombrar.
- **`category` no es opcional en la práctica**: aunque el builder defaultea a `CUSTOM`, elige siempre la categoría más específica de las 13 disponibles — es el filtro principal de `GET /runtime/capabilities`.
- **No uses `CapabilityMetadata` para servicios**: un servicio del `ServiceContainer` tiene su propio `ServiceMetadata` (ver [RUNTIME.md](../runtime/RUNTIME.md)) — una capacidad describe *qué* puede hacer el framework, un servicio describe *cómo* está cableado internamente.
