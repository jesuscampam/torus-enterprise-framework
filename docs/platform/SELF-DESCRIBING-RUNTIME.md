# Self-Describing Runtime — TEAF

Tres piezas responden, cada una desde un ángulo distinto, a la misma pregunta — "¿qué es y qué puede hacer esta instancia de TEAF ahora mismo?": `RuntimeSelfDescription`, `RuntimeDiagnostics` y `runtime.manifest.json`. Ver visión general en [PLATFORM-INTELLIGENCE.md](PLATFORM-INTELLIGENCE.md).

## 1. `RuntimeSelfDescription`

La respuesta "¿qué eres y qué puedes hacer?" (`backend/runtime/self_description.py`), servida por `GET /runtime/self` y `Runtime.self_description()`:

```python
description = runtime.self_description()

description.framework                  # "TEAF"
description.version                     # framework_version con el que se construyó el Runtime
description.runtime_state                # "bootstrapping" / "running" / "stopped"
description.modules                       # tuple[str, ...] — nombres del ModuleRegistry
description.services                       # tuple[str, ...] — service_id de cada servicio
description.capabilities                    # tuple[str, ...] — id de cada capacidad
description.plugins                          # tuple[str, ...] — name de cada plugin cargado
description.feature_flags                     # tuple[str, ...] — id de cada feature flag
description.supports_ai / supports_mcp / ...    # bool, uno por subsistema
description.supported_runtime_version             # str
description.supported_python_version                # str (sys.version)
```

Los campos `supports_*` (`ai`, `mcp`, `scheduler`, `database`, `storage`, `notifications`) se calculan comprobando si el módulo correspondiente está registrado en el `ModuleRegistry` (`registry.get(name) is not None`) — **no** si su implementación es real. En este Sprint todos los módulos de infraestructura están en `CONTRACTS_ONLY`, así que `supports_ai`/`supports_database`/etc. son `True` (el módulo existe y está registrado) mientras que `supports_mcp` es `False` (no existe todavía un módulo `"mcp"` registrado — ver [ROADMAP.md](../roadmap/ROADMAP.md)).

## 2. `RuntimeDiagnostics`

El diagnóstico operativo extendido (`backend/runtime/diagnostics.py`), servido por `GET /runtime/info` y `Runtime.diagnostics()`. Complementa — no sustituye — `RuntimeMetadata` (Sprint 2.3, `GET /info`): `RuntimeMetadata` es el resumen mínimo de arranque; `RuntimeDiagnostics` es la vista extendida de plataforma.

```python
diagnostics = runtime.diagnostics(configuration_summary={"environment": "production"})

diagnostics.runtime_id                  # uuid4, uno por instancia de Runtime
diagnostics.startup_time                 # datetime | None — None si nunca arrancó
diagnostics.running_time_seconds          # float, 0.0 si nunca arrancó
diagnostics.registered_modules            # int
diagnostics.registered_services            # int
diagnostics.registered_capabilities         # int
diagnostics.registered_plugins               # int
diagnostics.registered_features               # int
diagnostics.framework_version                   # str
diagnostics.python_version                        # str
diagnostics.configuration_summary                   # lo que le pases — Runtime no conoce Settings
diagnostics.dependency_graph_summary                  # {"nodes": N, "edges": N}
diagnostics.container_statistics                        # {"registeredContracts": N}
diagnostics.memory_placeholder / cpu_placeholder          # siempre "not-implemented" en este Sprint
```

`memory_placeholder`/`cpu_placeholder` son literales explícitos, no `None` ni campos ausentes — documentan a propósito la ausencia de la métrica (sin OpenTelemetry real en este Sprint) en vez de dejar que un consumidor la infiera de un campo faltante. Un Sprint futuro con observabilidad real los reemplaza sin cambiar la forma de `RuntimeDiagnostics`.

## 3. `ServiceDiscovery` — la pieza que alimenta ambas vistas

`backend/runtime/service_discovery.py` es una capa de solo lectura sobre `ServiceContainer.describe_services()` — no registra ni modifica nada:

```python
runtime.service_discovery.list()                       # tuple[ServiceMetadata, ...]
runtime.service_discovery.search("database")             # substring en service_id/name/tags
runtime.service_discovery.resolve(MyContract)              # delega en container.resolve()
runtime.service_discovery.describe("my-service")             # ServiceNotRegisteredException si no existe
runtime.service_discovery.capabilities("my-service")           # tuple[str, ...] declaradas en ServiceMetadata
runtime.service_discovery.dependency_tree("my-service")          # árbol recursivo, protegido contra ciclos
```

`dependency_tree` expande recursivamente `ServiceMetadata.dependencies` (nombres declarativos, no necesariamente otros contratos registrados) — un `service_id` ya visitado en la rama actual no se vuelve a expandir, evitando recursión infinita si dos servicios se declaran mutuamente dependientes.

## 4. `runtime.manifest.json`

Fotografía completa y serializable de la instancia, generada por `backend/runtime/manifest.py` (`generate_manifest()`/`write_manifest()`):

```json
{
  "framework": "TEAF",
  "version": "0.4.0-alpha",
  "runtime": { "...RuntimeSelfDescription.as_dict()..." },
  "modules": [ "...ModuleDescriptor.as_dict() por cada módulo..." ],
  "capabilities": [ "..." ],
  "services": [ "..." ],
  "plugins": [ "..." ],
  "configuration": { "...resumen no sensible..." },
  "featureFlags": [ "..." ],
  "contracts": [ "AIProvider", "CapabilityProvider", "..." ],
  "providers": [ "ai", "database", "security", "storage", "telemetry" ],
  "factories": [ "DatabaseFactory", "SecurityFactory" ]
}
```

Los tres últimos campos (`contracts`, `providers`, `factories`) son las **únicas** constantes estáticas del Sprint: nombres de clases/subpaquetes de `backend/contracts/` y `backend/providers/`, listados a mano en `KNOWN_CONTRACTS`/`KNOWN_PROVIDERS`/`KNOWN_FACTORIES` — deliberadamente, para no importar esos paquetes desde `backend/runtime/` y romper la regla de dependencias ya establecida ([RUNTIME.md](../runtime/RUNTIME.md)). Todo lo demás en el manifiesto se lee en vivo del `Runtime`.

### Cuándo se genera

`backend/core/application.py` lo escribe automáticamente en `_lifespan`, justo después de `runtime.startup()` — **excepto** cuando `settings.environment is Environment.TESTING`, para no ensuciar el repositorio en cada corrida de la suite de pruebas (`TestClient` dispara el mismo `lifespan` que un arranque real). Un fallo de escritura (por ejemplo, un filesystem de solo lectura en producción) se registra como advertencia y **no** tumba el arranque — es un artefacto de introspección, no una dependencia crítica del framework.

`runtime.manifest.json` se escribe siempre en la raíz del repositorio y está en `.gitignore` — es un artefacto generado, nunca una fuente de verdad editada a mano.

## 5. Feature Flags — el complemento operativo

Un feature flag responde una pregunta distinta a una capacidad: no "¿existe esta funcionalidad?" sino "¿está **activada** ahora mismo?". Vive en `backend/runtime/features/` — mismo espíritu que `CapabilityRegistry` ([CAPABILITY-REGISTRY.md](CAPABILITY-REGISTRY.md)), sin persistencia.

```python
from backend.runtime.features.flag import FeatureFlag
from backend.runtime.features.enums import FeatureGroup

flag = FeatureFlag(id="ai.embeddings", name="AI Embeddings", group=FeatureGroup.AI)
runtime.feature_manager.register(flag)   # registro directo, sin evento

runtime.enable_feature("ai.embeddings")    # wrapper de Runtime — publica "feature.enabled"
runtime.feature_manager.is_enabled("ai.embeddings")  # True
runtime.disable_feature("ai.embeddings")     # publica "feature.disabled"
```

`FeatureFlag` es un `dataclass` inmutable (`id`, `name`, `description`, `group`, `status`, `tags`, `created_at`, `updated_at`) — `enable()`/`disable()` no lo mutan, lo reemplazan por una copia con `status`/`updated_at` actualizados (`dataclasses.replace`). Siete grupos (`FeatureGroup`): `PLATFORM`, `SECURITY`, `DATABASE`, `AI`, `MCP`, `EXPERIMENTAL`, `INFRASTRUCTURE`. Todo flag nuevo nace `FeatureStatus.DISABLED` — activarlo es una acción explícita, nunca el valor por defecto.

`FeatureManager.list(group=...)` permite filtrar por grupo, igual que `CapabilityRegistry.list(category=...)`. Expuesto por `GET /runtime/features` y `api.features()` del Developer API.

## 6. Buenas prácticas

- **No leas `runtime.manifest.json` desde código que corre dentro del mismo proceso** — usa `generate_manifest(runtime)` directamente o el [Developer API](DEVELOPER-API.md); el archivo es para consumidores *externos* al proceso (scripts de despliegue, auditoría, un futuro dashboard).
- **`diagnostics()` necesita que le pases `configuration_summary`** si quieres que lo incluya — a diferencia de `self_description()`, no tiene un valor por defecto útil porque `Runtime` no conoce `Settings`.
- **`dependency_tree()` puede devolver ramas "hoja" para IDs no registrados** — un `service_id` declarado en `dependencies` pero nunca registrado en este `ServiceContainer` aparece como `{"id": "...", "dependencies": []}`, no como un error; es información válida (la dependencia existe conceptualmente aunque no esté cableada en este `Runtime`).
