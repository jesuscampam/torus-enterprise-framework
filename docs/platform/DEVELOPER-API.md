# Developer API — TEAF

El Developer API (`teaf/_internal/developer/runtime_api.py`, clase `DeveloperRuntimeAPI`) expone exactamente lo mismo que la [Runtime API](RUNTIME-API.md) HTTP, pero para código Python que corre **en el mismo proceso**: un script de mantenimiento, una consola interactiva, un plugin, o un futuro servidor MCP (ver Sprint 2.4, ítems 13 y 15). Ver visión general en [PLATFORM-INTELLIGENCE.md](PLATFORM-INTELLIGENCE.md).

> No depende de HTTP: no hay cliente, no hay serialización de red, no hay latencia de red. Es una fachada de solo lectura sobre un `Runtime` ya construido.

## 1. Por qué existe un paquete `teaf/_internal/developer/` separado

`teaf/_internal/developer/` es un paquete nuevo de Sprint 2.4, hermano de `teaf/_internal/runtime/`, no una subcarpeta de él — señala explícitamente que este código es **superficie de consumo**, no infraestructura del Runtime en sí. Nada en `teaf/_internal/runtime/` depende de `teaf/_internal/developer/` (la dependencia va en un solo sentido: `developer/` → `runtime/`).

## 2. `DeveloperRuntimeAPI`

```python
from teaf._internal.developer.runtime_api import DeveloperRuntimeAPI

api = DeveloperRuntimeAPI(runtime, configuration_provider=lambda: configuration_summary)

api.info()           # RuntimeDiagnostics.as_dict()
api.modules()         # list[ModuleDescriptor.as_dict()]
api.services()         # list[ServiceMetadata.as_dict()]
api.plugins()            # list[PluginMetadata.as_dict()]
api.capabilities()        # list[CapabilityMetadata.as_dict()]
api.features()              # list[FeatureFlag.as_dict()]
api.events(limit=10)         # list[{"name": ..., "payload": {...}}]
api.configuration()           # Mapping[str, object]
api.dependencies()             # {"modules": {...}, "services": [...]}
```

Nueve métodos, uno por cada superficie de introspección del Runtime salvo `self()` (la Runtime API HTTP sí expone `GET /runtime/self`; el Developer API no lo duplica — llama directamente a `runtime.self_description()` si lo necesitas, ver sección 4).

`configuration_provider` es el mismo mecanismo que usa la Runtime API HTTP (ver [RUNTIME-API.md, sección 4](RUNTIME-API.md#4-configurationprovider--cómo-llega-la-configuración-sin-romper-capas)) — por defecto, `default_configuration_provider()` devuelve `{}` si no se aporta ninguno.

## 3. Dónde se construye

`teaf/_internal/core/application.py` (el composition root) construye una instancia por aplicación y la expone en `app.state.developer_api` — no está montada en ningún router, es de uso puramente interno:

```python
app.state.developer_api = DeveloperRuntimeAPI(
    runtime, configuration_provider=lambda: configuration_summary
)
```

Cualquier código con acceso a `app.state` (un script de administración, un test, un futuro comando de CLI) puede usarla sin pasar por HTTP.

## 4. Cómo se evita duplicar lógica con la Runtime API

`DeveloperRuntimeAPI` no reimplementa el ensamblado de datos: importa las mismas funciones `build_*_payload` de `teaf/_internal/runtime/api.py` que usa el router HTTP.

```python
# teaf/_internal/developer/runtime_api.py
from teaf._internal.runtime.api import build_modules_payload, ...

class DeveloperRuntimeAPI:
    def modules(self) -> list[dict[str, object]]:
        return build_modules_payload(self._runtime)
```

Esto garantiza que `GET /runtime/modules` y `api.modules()` **siempre** devuelven exactamente la misma forma de datos — un cambio en el ensamblado se hace una vez y se refleja en ambos lados automáticamente. Para `self()`/`GET /runtime/self` no existe una función `build_*_payload` equivalente porque `Runtime.self_description()` ya es, en sí misma, el punto único de ensamblado — ambos lados lo llaman directamente.

## 5. Casos de uso previstos

- **Scripts de mantenimiento**: un script que verifica que ciertas capacidades críticas están registradas antes de considerar el despliegue exitoso.
- **Consola interactiva** (`python -c`, REPL): inspeccionar el estado de una instancia sin levantar un cliente HTTP.
- **Un futuro servidor MCP** (Sprint posterior): en vez de hacer peticiones HTTP a sí mismo, un proceso MCP embebido en el mismo runtime puede consumir `DeveloperRuntimeAPI` directamente — cero overhead de red para algo que ya vive en el mismo proceso.
- **Plugins** (cuando existan implementaciones reales de `Plugin`): un plugin cargado por `PluginLoader` puede recibir o construir un `DeveloperRuntimeAPI` para introspeccionar el Runtime que lo cargó.

## 6. Buenas prácticas

- **Es de solo lectura**: ningún método de `DeveloperRuntimeAPI` registra ni modifica nada — para eso están los wrappers de `Runtime` (`register_capability`, `enable_feature`, etc.), no esta fachada.
- **No la uses como sustituto de `Runtime` directo dentro de `teaf/_internal/runtime/`** — es una capa de conveniencia para consumidores externos al Runtime, no para código interno del propio paquete.
- **Si necesitas un método nuevo, añade primero su `build_*_payload`** en `teaf/_internal/runtime/api.py` (ver [RUNTIME-API.md, sección 5](RUNTIME-API.md#5-reutilización-con-el-developer-api)) y expónlo desde ambos lados.
