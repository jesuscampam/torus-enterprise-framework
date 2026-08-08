# Runtime API — TEAF

La Runtime API expone por HTTP, bajo el prefijo `GET /runtime/*`, todo lo que el `Runtime` sabe de sí mismo en el momento de la petición. Vive en `teaf/_internal/runtime/api.py`, montada en `teaf/_internal/core/application.py` junto al resto de routers de sistema. Ver visión general en [PLATFORM-INTELLIGENCE.md](PLATFORM-INTELLIGENCE.md).

> Toda la información expuesta se lee del `Runtime` en vivo — nunca datos simulados ni cacheados entre peticiones (ver Sprint 2.4, ítem 7).

## 1. Por qué vive dentro de `teaf/_internal/runtime/` y no en `teaf/_internal/monitoring/`

`teaf/_internal/monitoring/info.py` (Sprint 2.2/2.3) depende únicamente de `teaf/_internal/core/` — nunca importa `teaf/_internal/runtime/` directamente, recibe el estado del Runtime como un `Callable` genérico para no cruzar esa frontera. La Runtime API necesita acceso profundo al `Runtime` (su `container`, `capability_registry`, `feature_manager`, `event_bus`...), así que vive **dentro** de `teaf/_internal/runtime/` — es el propio Runtime describiéndose, no Monitoring extendiendo su alcance más allá de lo que le corresponde.

## 2. Los 10 endpoints

Todos devuelven JSON, sin autenticación en este Sprint (se añadirá cuando Security deje de ser `contracts_only`).

| Endpoint | Devuelve |
|---|---|
| `GET /runtime/info` | `RuntimeDiagnostics.as_dict()` — ver [SELF-DESCRIBING-RUNTIME.md](SELF-DESCRIBING-RUNTIME.md#2-runtimediagnostics). |
| `GET /runtime/modules` | Lista de `ModuleDescriptor.as_dict()` — todos los módulos del `ModuleRegistry`. |
| `GET /runtime/services` | Lista de `ServiceMetadata.as_dict()` — `ServiceDiscovery.list()`. |
| `GET /runtime/plugins` | Lista de `PluginMetadata.as_dict()` — plugins cargados en `PluginLoader`. |
| `GET /runtime/capabilities` | Lista de `CapabilityMetadata.as_dict()` — `CapabilityRegistry.list()`. |
| `GET /runtime/features` | Lista de `FeatureFlag.as_dict()` — `FeatureManager.list()`. |
| `GET /runtime/events` | Historial del `EventBus` (`?limit=N` opcional) — `[{"name": ..., "payload": {...}}, ...]`. |
| `GET /runtime/configuration` | Resumen de configuración no sensible, aportado por el composition root. |
| `GET /runtime/dependencies` | `{"modules": {...grafo...}, "services": [árboles de dependencia por servicio]}`. |
| `GET /runtime/self` | `RuntimeSelfDescription.as_dict()` — ver [SELF-DESCRIBING-RUNTIME.md](SELF-DESCRIBING-RUNTIME.md#1-runtimeselfdescription). |

## 3. Ejemplo

```bash
curl http://localhost:8000/runtime/self
```

```json
{
  "framework": "TEAF",
  "version": "0.4.0-alpha",
  "runtimeState": "running",
  "modules": ["database", "security", "telemetry", "storage", "ai", "scheduler", "notification"],
  "services": [],
  "capabilities": [],
  "plugins": [],
  "featureFlags": [],
  "supports": {
    "ai": true, "mcp": false, "scheduler": true,
    "database": true, "storage": true, "notifications": true
  },
  "supportedRuntimeVersion": "0.4.0-alpha",
  "supportedPythonVersion": "3.11.15 (...)"
}
```

## 4. `ConfigurationProvider` — cómo llega la configuración sin romper capas

`Runtime` nunca importa `teaf/_internal/config/` (la misma regla de Sprint 2.3: "Runtime solo depende de Core"). `GET /runtime/configuration` y `GET /runtime/info` necesitan, sin embargo, un resumen de la configuración activa. La solución es la misma que ya usa `teaf/_internal/monitoring/info.py` desde Sprint 2.2: un `Callable` inyectado desde fuera.

```python
# teaf/_internal/runtime/api.py
ConfigurationProvider = Callable[[], Mapping[str, object]]

def create_runtime_router(
    runtime: Runtime,
    *,
    configuration_provider: ConfigurationProvider = default_configuration_provider,
) -> APIRouter: ...
```

`teaf/_internal/core/application.py` (el composition root, el único lugar con acceso a `Settings`) construye el resumen no sensible y lo pasa al montar el router:

```python
app.include_router(
    create_runtime_router(runtime, configuration_provider=lambda: configuration_summary)
)
```

Ningún campo de `Settings` actual es secreto — si un Sprint futuro añade credenciales reales, `_configuration_summary()` (`teaf/_internal/core/application.py`) deberá excluirlas explícitamente antes de exponerlas por esta ruta.

## 5. Reutilización con el Developer API

Las funciones `build_modules_payload`, `build_services_payload`, `build_plugins_payload`, `build_capabilities_payload`, `build_features_payload`, `build_events_payload` y `build_dependencies_payload` (todas en `teaf/_internal/runtime/api.py`) son el único punto donde se ensamblan estas respuestas. El [Developer API](DEVELOPER-API.md) las reutiliza directamente — la única diferencia entre consumir TEAF por HTTP o en proceso es la capa de transporte, nunca la forma de los datos. Si añades un endpoint nuevo, añade primero su función `build_*_payload` y expónla en ambos lados.

## 6. Buenas prácticas

- **No añadas lógica de negocio a los handlers del router** — cada uno es una línea: llama a una función `build_*_payload` (o a un método de `Runtime`) y devuelve el resultado. Cualquier lógica adicional pertenece a `Runtime` o a las piezas que compone.
- **`GET /runtime/events?limit=N`** existe para no forzar a un cliente a descargar todo el historial — úsalo en dashboards o integraciones que solo necesitan los últimos eventos.
- **No expongas esta API sin autenticación en producción** una vez `Security` deje de ser `contracts_only` — revela la topología interna del framework (módulos, servicios, dependencias).
