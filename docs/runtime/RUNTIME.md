# Runtime del Framework — TEAF

Documentación del Runtime implementado en el Sprint 2.3 (Framework Runtime, v0.3.0-alpha): la infraestructura que permite ejecutar módulos dentro de TEAF — contenedor de servicios, ciclo de vida, pipelines, descubrimiento de módulos, grafo de dependencias, bus de eventos y carga de plugins. Complementa — no reemplaza — [FRAMEWORK-BLUEPRINT.md](../architecture/FRAMEWORK-BLUEPRINT.md), [docs/core/CORE.md](../core/CORE.md) (Sprint 2.1) y [docs/infrastructure/INFRASTRUCTURE.md](../infrastructure/INFRASTRUCTURE.md) (Sprint 2.2).

> Ningún módulo de negocio, servicio externo ni implementación concreta se conecta en este Sprint. `Runtime` es deliberadamente **independiente de `teaf/_internal/contracts/` y `teaf/_internal/providers/`** — no los importa en ningún archivo.

## 1. Arquitectura

```
teaf/_internal/runtime/
├── container.py               # ServiceContainer, Lifetime, ServiceScope, Lazy
├── lifecycle.py                 # LifecycleManager, LifecycleStage
├── pipeline.py                   # Pipeline, StartupPipeline, ShutdownPipeline
├── discovery.py                   # ModuleDiscovery
├── dependency_graph.py             # DependencyGraph
├── event_bus.py                     # Event, EventBus
├── plugin_loader.py                   # Plugin, PluginLoader
├── configuration_pipeline.py           # ConfigurationPipeline
├── exceptions.py                        # Excepciones del Runtime (heredan de InfrastructureException)
├── hooks.py                              # Utilidad interna: invocar hooks síncronos o asíncronos
└── runtime.py                             # Runtime — orquestador que compone todo lo anterior
```

`Runtime` es al ciclo de vida del framework lo que `teaf/_internal/core/application.py` es a la aplicación FastAPI: un composition root local. Solo `runtime.py` conoce y ensambla el resto de piezas del paquete; cada pieza individual (`container.py`, `lifecycle.py`, etc.) es independiente entre sí salvo por las utilidades compartidas (`exceptions.py`, `hooks.py`).

**Dependencias declaradas**: `teaf/_internal/runtime/` → `teaf/_internal/core/` únicamente (`ModuleRegistry`, `ModuleDescriptor`, `ModuleStatus`, `ApplicationException`/`InfrastructureException`/`ConfigurationException`). `teaf/_internal/core/application.py` (composition root de la aplicación) importa `teaf/_internal/runtime/`, igual que ya importaba `config/`, `middleware/`, `monitoring/` y `providers/` desde Sprint 2.1/2.2.

## 2. Ciclo de vida (`LifecycleManager`)

Cinco etapas, en orden: **Bootstrap → Startup → Running → Shutdown → Stopped**. Cualquier pieza puede registrar un hook (síncrono o asíncrono) para una etapa con `lifecycle.on(stage, hook)`; `Runtime.startup()`/`Runtime.shutdown()` avanzan las etapas invocando sus hooks en orden de registro.

```mermaid
flowchart LR
    B[Bootstrap] --> S[Startup] --> R[Running] --> SD[Shutdown] --> ST[Stopped]
```

Un hook que falla lanza `LifecycleException`, indicando la etapa y el índice del hook — el arranque/apagado se detiene ahí, no continúa a ciegas.

## 3. Startup Pipeline y Shutdown Pipeline

Ambos son `Pipeline` con pasos nombrados (`add_step(name, action)`), pero difieren en el orden de ejecución:

- **`StartupPipeline`**: FIFO — los pasos corren en el orden en que se registraron. Cada módulo futuro añade aquí su propia secuencia de inicialización.
- **`ShutdownPipeline`**: LIFO — los pasos corren en **orden inverso**. El último recurso adquirido es el primero en liberarse, la práctica estándar de limpieza de recursos.

`Runtime.startup()` ejecuta `StartupPipeline` durante la etapa `STARTUP`; `Runtime.shutdown()` ejecuta `ShutdownPipeline` al empezar el apagado, antes de avanzar a la etapa `SHUTDOWN`.

## 4. Service Container

`ServiceContainer` resuelve dependencias por contrato (cualquier `type`, no necesariamente una interfaz de `contracts/`). Tres ciclos de vida:

| Lifetime | Comportamiento |
|---|---|
| `SINGLETON` | Una única instancia por contenedor, creada en el primer `resolve()`. |
| `SCOPED` | Una instancia por `ServiceScope` (`container.create_scope()`), compartida solo dentro de ese `with`. |
| `TRANSIENT` | Una instancia nueva en cada `resolve()`. |

Todas las factories son perezosas (no se invocan hasta el primer `resolve()`) y pueden resolver otras dependencias del propio contenedor (reciben el contenedor como argumento). `resolve_lazy(contract)` devuelve un `Lazy[T]` cuyo valor se calcula solo al acceder a `.value`. Una cadena de factories que se resuelven entre sí de forma circular lanza `CircularDependencyException` con la cadena completa en el mensaje.

```python
container.register_singleton(MyContract, lambda c: MyImplementation())
instance = container.resolve(MyContract)
```

## 5. Module Discovery y Dependency Graph

`ModuleDiscovery` lee el `ModuleRegistry` (Sprint 2.2) — "descubrir" en este Sprint significa consultar el registro ya poblado por el composition root, no escanear el filesystem.

`DependencyGraph` se construye a partir de `ModuleDescriptor.dependencies` (campo añadido de forma aditiva en este Sprint) y ofrece `detect_cycle()` / `topological_order()`. `Runtime.startup()` llama a `topological_order()` durante `BOOTSTRAP`, **antes** de correr el `StartupPipeline` — un ciclo aborta el arranque con `CircularDependencyException` en vez de fallar de forma confusa a mitad de la inicialización.

Ejemplo real ya cableado en `teaf/_internal/core/application.py`: el módulo `ai` declara `dependencies=("security",)`, reflejando la regla ya fijada en [FRAMEWORK-BLUEPRINT.md, sección 5](../architecture/FRAMEWORK-BLUEPRINT.md#5-mapa-de-dependencias) (AI depende de Security).

## 6. Internal Event Bus

`EventBus` es pub/sub síncrono, **exclusivamente en proceso** — sin cola, sin broker, sin entrega distribuida. `Runtime` publica `framework.startup.completed` y `framework.shutdown.completed`; cualquier pieza puede suscribirse sin que `Runtime` conozca a sus suscriptores.

```python
runtime.event_bus.subscribe("framework.startup.completed", lambda event: ...)
```

## 7. Plugin Loader

`Plugin` es el contrato mínimo (`name`, `version`, `register(container)`) que un plugin futuro deberá cumplir. `PluginLoader.load(plugin, container=...)` valida (nombre/versión presentes, no duplicado) y ejecuta `plugin.register(container)`. Sin plugins reales ni descubrimiento automático (filesystem/entry points) en este Sprint — ambos son extensiones naturales sin cambiar el contrato ya definido.

## 8. Configuration Pipeline

Cada módulo puede registrar un validador (`configuration_pipeline.register(module_name, validator)`) — una función sin argumentos que lanza si su configuración es inválida. `Runtime.startup()` ejecuta `validate_all()` durante `BOOTSTRAP`, antes de comprobar el grafo de dependencias: una configuración inválida detiene el arranque con `ConfigurationException` (reutilizando la excepción ya definida en Sprint 2.1) antes de que nada más se inicialice.

## 9. Runtime Metadata (`GET /info`)

`Runtime.describe()` devuelve una fotografía (`RuntimeMetadata`) con:

- `state`: `bootstrapping` / `running` / `stopped`.
- `lifecycle_stage`: la última etapa de `LifecycleManager` completada.
- `loaded_modules`: nombres de los módulos del `ModuleRegistry`.
- `registered_capabilities`: nombres de los contratos con proveedor registrado en el `ServiceContainer` (vacío en este Sprint — nada se registra todavía).

`GET /info` la expone fusionada con la información ya existente de versión y módulos (Sprint 2.2). `teaf/_internal/monitoring/info.py` **no importa `teaf/_internal/runtime/`**: recibe un `Callable[[], dict]` que el composition root construye a partir de `runtime.describe().as_dict()`, preservando la regla "Monitoring depende únicamente de Core" y garantizando que cada petición lea el estado actual (no una fotografía capturada una vez al arrancar).

## 10. Buenas prácticas para extender el Runtime

- **No registrar nada directamente en `container.py`, `lifecycle.py`, etc.** — esas piezas son genéricas. El cableado específico de un módulo va en el composition root (`teaf/_internal/core/application.py`) o, en el futuro, en el propio módulo durante su fase de registro.
- **Todo hook/paso debe ser idempotente si es razonablemente posible** — un reintento de arranque no debería dejar el sistema en un estado inconsistente.
- **`ShutdownPipeline` es LIFO a propósito**: si un paso de `StartupPipeline` adquiere un recurso, el paso de `ShutdownPipeline` que lo libera debe registrarse en el mismo momento (no al final), para que el orden inverso sea correcto automáticamente.
- **Nunca importar `teaf/_internal/contracts/` ni `teaf/_internal/providers/` desde `teaf/_internal/runtime/`** — si una pieza del Runtime necesita conocer un contrato concreto, esa lógica pertenece al composition root, no al Runtime genérico.
- **Los eventos del `EventBus` son solo para desacoplar piezas internas del framework**, no un mecanismo de mensajería de negocio — no publiques eventos de dominio de una aplicación aquí.

## 11. Qué NO incluye este Sprint

Sin PostgreSQL, sin SQLAlchemy funcional, sin JWT/OAuth, sin usuarios, sin React, sin Docker, sin Azure, sin IA, sin MCP, sin scheduler funcional, sin notificaciones, sin storage real. Todo eso llega en Sprints posteriores (ver [ROADMAP.md](../roadmap/ROADMAP.md)).
