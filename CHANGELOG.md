# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

Sin cambios todavía sobre [0.5.0-alpha](#050-alpha---2026-08-03).

## [0.5.0-alpha] - 2026-08-03

### Added

- **Module SDK** (Sprint 2.5, Developer Platform): paquete nuevo `backend/sdk/`, dependiente de `backend/core/` y `backend/runtime/` (a diferencia de `backend/runtime/`, que nunca depende de `contracts/`/`providers/` — el SDK sí depende del Runtime: es la capa de autoría de alto nivel apoyada en él). Un desarrollador crea un módulo completo heredando únicamente de `ModuleBase`.
  - **Primitivas de descripción**: `ModuleDescriptor` (metadata de autoría, homónimo deliberado de `backend.core.registry.ModuleDescriptor`), `ModuleConfiguration`, `ModuleHealth` (reutiliza `CapabilityHealth`), `ModuleCapability`, `ModuleService`, `ModuleDependency`, `ModuleCategory` (7 valores).
  - **`ModuleManifest`**: compone `ModuleDescriptor` + license/capabilities/dependencies/configuration/services/health_checks/events/runtime_compatibility/sdk_compatibility, con `as_dict()` aplanado.
  - **`ModuleSpecification v1`** (`specification.py`): diez secciones formales (Metadata, Lifecycle, Dependencies, Capabilities, Configuration, Services, Health, Documentation, Packaging, Validation Rules).
  - **`ModuleBuilder`** (`builder.py`): builder fluido — `with_*`/`add_*`/`build()` — única forma probada de construir un `ModuleManifest`.
  - **`ModuleValidator`** (`validator.py`): valida metadata (slug/semver), duplicados (capacidades/servicios/configuración/health checks/dependencias), auto-dependencias y compatibilidad Runtime/SDK; `validate()`, `validate_or_raise()`, `errors_by_section()`.
  - **`ModuleDependencyResolver`** (`dependency_resolver.py`): resuelve orden de inicialización entre varios manifiestos, detecta ciclos (reutilizando `backend.runtime.dependency_graph.DependencyGraph` vía un adaptador estructural), detecta conflictos de versión, construye árboles de dependencias.
  - **`ServiceBinder`/`CapabilityBinder`** (`service_binder.py`, `capability_binder.py`): traducen `ModuleService`/`ModuleCapability` en registros reales contra `Runtime.register_service`/`register_capability` — el autor del módulo nunca llama al `ServiceContainer`/`CapabilityRegistry` directamente.
  - **`ModuleContext`** (`context.py`): envuelve un `Runtime` + configuración + logger con nombre; atajos `.container`, `.capabilities`, `.features`, `.events`.
  - **`ModuleBase`** (`module_base.py`): la única clase de la que hereda un módulo. Siete hooks opcionales, síncronos o asíncronos (`initialize`, `configure`, `register`, `start`, `ready`, `stop`, `dispose`); `bootstrap()`/`shutdown()` orquestan validación, comprobación de compatibilidad, registro en `ModuleRegistry`, enlace automático de servicios/capacidades y ejecución de hooks, avanzando `ModuleLifecycle` en cada paso.
  - **`ModuleLifecycle`/`ModuleLifecycleState`** (`lifecycle.py`): ocho estados (created → initialized → configured → registered → started → ready → stopped → disposed, más `failed` terminal alcanzable desde cualquier punto), con historial y protección contra retrocesos.
  - **`ModuleInspector`** (`inspector.py`): introspección de solo lectura — `describe`/`services`/`capabilities`/`dependencies`/`events`/`configuration`/`health`/`manifest`.
  - **`MODULE_TEMPLATES`/`ModuleScaffolder`** (`templates.py`, `scaffolder.py`): 7 plantillas (Generic, Database, Security, Storage, Integration, AI, MCP), sin código de negocio; `scaffold()` genera un esqueleto en memoria (Python válido), `write_to_disk()` lo materializa como paso explícito — sin CLI.
  - **`ModuleDocumentationGenerator`** (`documentation_generator.py`): genera Markdown a partir de un `ModuleManifest` — solo el servicio, sin escribir archivos.
  - **`ModuleCertification`** (`certification.py`): certifica ocho secciones (Specification, Manifest, Metadata, Capabilities, Dependencies, Version, Health, Documentation) — más estricta que `ModuleValidator` en `documentation` (requerida para certificar, no para registrarse).
  - Cinco excepciones nuevas: `ModuleValidationException`, `ModuleCompatibilityException`, `ModuleDependencyException`, `ModuleRegistrationException`, `ModuleLifecycleException`.
- 130 pruebas nuevas (342 en total): primitivas, manifiesto/especificación, builder, validador, resolutor de dependencias, binders, `ModuleBase`/`ModuleContext` (incluye todos los caminos de fallo y comparador de compatibilidad), inspector, plantillas/scaffolder, generador de documentación, certificación. Cobertura del código nuevo de Sprint 2.5: 100%.
- `docs/sdk/` (6 documentos): `SDK.md`, `MODULE-SPECIFICATION.md`, `MODULE-BUILDER.md`, `MODULE-LIFECYCLE.md`, `MODULE-CERTIFICATION.md`, `DEVELOPER-GUIDE.md`.

### Changed

- Versión del framework: `0.4.0-alpha` → `0.5.0-alpha`.

### Notes

- Sprint 2.5 es exclusivamente infraestructura de autoría: ningún módulo real (Database, Security, AI, ...) se implementa con el SDK todavía — sin CLI, sin generación de proyectos completos, sin persistencia de módulos, sin Database/Security/Storage/Scheduler/OpenTelemetry/Azure/MCP/AI reales.
- Verificado sin dependencias circulares; `backend/sdk/` depende de `backend/core/` y `backend/runtime/` en un solo sentido (ningún archivo de `runtime/`/`core/` importa `sdk/`); el arranque real (`uvicorn`) sigue sirviendo correctamente sin ningún módulo SDK cableado en `application.py` (el SDK es opt-in, no se auto-carga).

## [0.4.0-alpha] - 2026-08-03

### Added

- **Platform Intelligence** (Sprint 2.4): el Runtime gana la capacidad de describirse a sí mismo — extiende, no reemplaza, la infraestructura de Sprint 2.3.
  - **Capability Model** (`backend/runtime/capabilities/`): `CapabilityMetadata` (17 campos), `Capability`, `CapabilityCategory` (13 valores), `CapabilityStatus`, `CapabilityHealth`, `CapabilityBuilder` (fluido) y `CapabilityRegistry` (`register`/`unregister`/`find`/`exists`/`list`/`search`/`describe`). Ninguna capacidad real registrada.
  - `CapabilityProviderRegistry` (`provider_registry.py`): agregación de capacidades de múltiples proveedores vía un `typing.Protocol` estructural (`CapabilityProviderLike`), sin importar `backend/contracts/` — preparación para un futuro servidor MCP, sin implementarlo.
  - **Feature Flags** (`backend/runtime/features/`): `FeatureFlag`, `FeatureManager` (`register`/`enable`/`disable`/`exists`/`is_enabled`/`list`/`describe`), `FeatureGroup` (7 valores: Platform, Security, Database, AI, MCP, Experimental, Infrastructure), `FeatureStatus`. Sin persistencia.
  - `ModuleDescriptor` (`backend/core/registry.py`) gana campos aditivos: `author`, `description`, `lifecycle_state` (nuevo `ModuleLifecycleState`, propio de Core), `capabilities`, `tags`, `documentation`, `experimental`, `created_at`, `updated_at`, propiedad `id` y `as_dict()`; `ModuleRegistry` gana `unregister()`.
  - `Plugin` (`backend/runtime/plugin_loader.py`) gana la propiedad `metadata` (`PluginMetadata`, derivada por defecto de `name`/`version`); `PluginLoader` gana `unload()`.
  - `ServiceContainer` (`backend/runtime/container.py`) gana `ServiceMetadata`, `ServiceHealth`, registro opcional de metadata en `register_singleton`/`register_scoped`/`register_transient`/`register_instance`, `unregister()` y `describe_services()`.
  - `EventBus` (`backend/runtime/event_bus.py`) gana historial acotado (`history_limit`, `history(limit=...)`) — retiene los eventos publicados aunque no haya suscriptores.
  - `ServiceDiscovery` (`backend/runtime/service_discovery.py`): `list`/`search`/`resolve`/`describe`/`capabilities`/`dependency_tree` (con protección contra ciclos) sobre `ServiceContainer`.
  - `RuntimeDiagnostics` (`backend/runtime/diagnostics.py`) y `RuntimeSelfDescription` (`backend/runtime/self_description.py`): las dos fotografías extendidas del estado del Runtime, servidas por `Runtime.diagnostics()`/`Runtime.self_description()`.
  - `Runtime` (`backend/runtime/runtime.py`) gana: atributos compuestos `capability_registry`, `feature_manager`, `capability_provider_registry`, `service_discovery`, `framework_version`, `modules`; wrappers `register_module`/`unregister_module`, `register_service`/`remove_service`/`resolve_service`, `register_capability`/`remove_capability`, `load_plugin`/`unload_plugin`, `enable_feature`/`disable_feature` (cada uno publica su evento correspondiente en el `EventBus`); eventos nuevos `framework.started`/`framework.stopped` (junto a los ya existentes, por compatibilidad), `module.registered`/`module.unregistered`, `service.registered`/`service.removed`/`service.resolved`, `capability.registered`/`capability.removed`, `plugin.loaded`/`plugin.unloaded`, `feature.enabled`/`feature.disabled`.
  - **Runtime API** (`backend/runtime/api.py`, `GET /runtime/*`): `info`, `modules`, `services`, `plugins`, `capabilities`, `features`, `events` (con `?limit=`), `configuration`, `dependencies`, `self` — 10 endpoints, toda la información leída en vivo del Runtime.
  - **Developer API** (`backend/developer/runtime_api.py`, paquete nuevo): `DeveloperRuntimeAPI` — mismas 9 superficies de consulta que la Runtime API (salvo `self`), sin HTTP, reutilizando las funciones `build_*_payload` del router para no duplicar el ensamblado de datos.
  - **Runtime Manifest** (`backend/runtime/manifest.py`): `generate_manifest()`/`write_manifest()` producen `runtime.manifest.json` (Framework, Version, Runtime, Modules, Capabilities, Services, Plugins, Configuration, Feature Flags, Contracts, Providers, Factories) — generado automáticamente al arrancar (excepto en `TESTING`), gitignored.
  - Contratos nuevos en `backend/contracts/`: `CapabilityProvider` y `FrameworkKnowledgeProvider` — preparación para IA/MCP, sin implementación.
  - `backend/core/application.py`: monta `create_runtime_router`, construye `DeveloperRuntimeAPI`, genera `runtime.manifest.json` en `_lifespan` (guardado ante `OSError`), y expone `_configuration_summary()` como fuente única del resumen de configuración no sensible.
- 96 pruebas nuevas (212 en total): Capability Model, Feature Flags, Service Discovery, extensiones de `Runtime` (wrappers + eventos + `diagnostics()`/`self_description()`), Runtime Manifest, Developer API, Runtime API (integración HTTP) y extensiones de `ModuleDescriptor`/`PluginMetadata`/`ServiceMetadata`/`EventBus`. Cobertura del código nuevo de Sprint 2.4: 100%.
- `docs/platform/` (5 documentos): `PLATFORM-INTELLIGENCE.md`, `CAPABILITY-REGISTRY.md`, `RUNTIME-API.md`, `DEVELOPER-API.md`, `SELF-DESCRIBING-RUNTIME.md`.

### Changed

- Versión del framework: `0.3.0-alpha` → `0.4.0-alpha`.
- `.gitignore`: nueva entrada `runtime.manifest.json` (artefacto generado, nunca versionado).

### Notes

- Sprint 2.4 es exclusivamente infraestructura de introspección: ninguna capacidad, feature flag ni plugin real se registra — sin persistencia, sin IA, sin MCP, sin autenticación en la Runtime API todavía.
- Verificado sin dependencias circulares, `backend/runtime/` sigue sin importar `backend/contracts/` ni `backend/providers/` (incluida la nueva preparación para MCP, resuelta con `typing.Protocol` estructural), y el arranque real (`uvicorn`) sirve correctamente los 10 endpoints de `/runtime/*` además de `/info`.

## [0.3.0-alpha] - 2026-08-02

### Added

- **Framework Runtime** (Sprint 2.3): paquete `backend/runtime/`, independiente de `contracts/`/`providers/` (solo depende de `backend/core/`):
  - `ServiceContainer` (`container.py`): resolución por contrato con ciclos de vida Singleton/Scoped/Transient, resolución perezosa (`resolve_lazy`/`Lazy[T]`), factories que resuelven otras dependencias, y detección de dependencias circulares (`CircularDependencyException`).
  - `LifecycleManager` (`lifecycle.py`): cinco etapas (Bootstrap → Startup → Running → Shutdown → Stopped) con hooks síncronos o asíncronos por etapa.
  - `StartupPipeline`/`ShutdownPipeline` (`pipeline.py`): pasos nombrados, FIFO en el arranque y LIFO en el apagado.
  - `ModuleDiscovery` (`discovery.py`): lectura del `ModuleRegistry` con filtro opcional por estado.
  - `DependencyGraph` (`dependency_graph.py`): grafo de dependencias entre módulos con detección de ciclos y orden topológico, verificado antes de correr el `StartupPipeline`.
  - `EventBus` (`event_bus.py`): publicación/suscripción síncrona interna, sin mensajería distribuida.
  - `PluginLoader` (`plugin_loader.py`): contrato `Plugin` mínimo y mecanismo de carga/validación, sin plugins reales.
  - `ConfigurationPipeline` (`configuration_pipeline.py`): validadores de configuración por módulo, ejecutados antes de verificar el grafo de dependencias.
  - `Runtime` (`runtime.py`): orquestador que compone todo lo anterior; conectado al ciclo de vida de FastAPI vía `lifespan` en `backend/core/application.py`.
- `ModuleDescriptor` (`backend/core/registry.py`) gana el campo aditivo `dependencies: tuple[str, ...]` — el módulo `ai` ya declara `("security",)`, reflejando la regla ya fijada en FRAMEWORK-BLUEPRINT.md.
- `GET /info` ampliado con `state`, `lifecycleStage`, `loadedModules` y `registeredCapabilities` del Runtime, leídos en cada petición (no una fotografía capturada al arrancar).
- 60 pruebas nuevas (116 en total): Service Container, Lifecycle, Pipelines, Event Bus, Module Discovery, Dependency Graph, Plugin Loader, Configuration Pipeline y el `Runtime` orquestador — sin integraciones con servicios reales.
- `docs/runtime/RUNTIME.md` documenta la arquitectura del Runtime, el ciclo de vida, el registro de módulos, el contenedor de servicios, el event bus, el plugin loader y las buenas prácticas de extensión.

### Changed

- Versión del framework: `0.2.0-alpha` → `0.3.0-alpha`.
- `backend/core/application.py`: ahora usa `lifespan` de FastAPI para arrancar/apagar el `Runtime`; `/info` recibe un `Callable` que lee el estado del Runtime en vivo en vez del registro estático anterior.

### Notes

- Sprint 2.3 es exclusivamente infraestructura de ejecución: Service Container, ciclo de vida, pipelines, descubrimiento, grafo de dependencias, event bus y plugin loader — sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, scheduler, notificaciones ni storage reales, sin Docker ni Azure).
- Verificado sin dependencias circulares a nivel de archivo y que `backend/core/` (salvo `application.py`, el composition root ya documentado) sigue sin depender de ningún otro módulo del framework.

## [0.2.0-alpha] - 2026-08-02

### Added

- Estructura inicial del monorepo del framework: `backend/`, `frontend/`, `database/`, `docker/`, `scripts/`, `tests/`, `docs/`, `.github/`.
- Documentación base de arquitectura: `docs/architecture/ARCHITECTURE.md` y `docs/architecture/STACK.md`.
- Roadmap del framework con 5 versiones planificadas: `docs/roadmap/ROADMAP.md`.
- Primeros 5 Architecture Decision Records (ADR-001 a ADR-005) sobre FastAPI, PostgreSQL, Docker, API First y Cloud Ready.
- Estándares obligatorios del framework: API, base de datos, código, seguridad y logging (`docs/standards/`).
- Gobernanza de GitHub: `CODEOWNERS`, plantillas de Issues y Pull Request, `CONTRIBUTING.md`.
- Licencia MIT del proyecto.
- `CLAUDE.md`, `/templates/` (9 plantillas reutilizables), estándar de Git (`GIT-STANDARD.md`), backlog inicial (`BACKLOG.md`), catálogo de módulos (`MODULE-CATALOG.md`), quality gates, definition of done y glosario del proyecto.
- Framework Blueprint oficial (`docs/architecture/FRAMEWORK-BLUEPRINT.md`) con 12 diagramas Mermaid (arquitectura por capas, mapa de dependencias, flujos de inicialización/petición/excepción, arquitectura física de despliegue, arquitectura de seguridad, proveedores de IA y MCP) y documentos complementarios `NFR.md`, `DECISION-TREE.md`, `EXTENSIBILITY.md`.
- **Bootstrap ejecutable del framework** (Sprint 2.1): Application Factory (`backend/core/application.py`), configuración por entorno (Development/Testing/Staging/Production), logging estructurado (consola/JSON/archivo con rotación), jerarquía de excepciones (`ApplicationException` y 6 subtipos), middlewares de correlation-id y logging de peticiones, manejo centralizado de errores en formato RFC 7807, rutas de sistema (`/`, `/health`, `/live`, `/ready`), utilidades genéricas en `shared/`, y suite de pruebas base (`tests/unit/`, `tests/integration/`). Documentado en `docs/core/CORE.md`.
- Manifiestos de dependencias del backend (`requirements.txt`, `requirements-dev.txt`) y configuración de herramientas (`pyproject.toml`: ruff, black, mypy, pytest).
- **Infrastructure Foundation** (Sprint 2.2): paquete `backend/contracts/` con 9 interfaces puras (Repository, UnitOfWork, DatabaseProvider, Authentication/AuthorizationProvider, TelemetryProvider, StorageProvider, AIProvider, SchedulerProvider, NotificationProvider); paquete `backend/providers/` con clases base y factories abstractas para database (`DatabaseFactory`, `DatabaseSession`, `ConnectionManager`, `RepositoryBase`), security (`SecurityContext`, `AuthenticationManager`, `AuthorizationManager`, RBAC, `SecurityFactory`), telemetry (`TracerProvider`, `MetricsProvider`, `LoggerProvider`, `TelemetryContext`), storage y ai; `ModuleRegistry` (`backend/core/registry.py`) registrado por instancia de aplicación (no como singleton de proceso); expansión de la inyección de dependencias (`backend/providers/dependencies.py`); nueva ruta `/info` con versión y estado de los módulos registrados. Documentado en `docs/infrastructure/INFRASTRUCTURE.md`. 32 pruebas nuevas (contracts, registry, factories, DI) — sin integraciones reales.

### Changed

- `README.md`: la sección "Cómo iniciar el proyecto" ahora documenta pasos reales de arranque (`uvicorn backend.main:app --reload`), en vez de la nota de "sin código ejecutable" de la iteración de fundación.
- Versión del framework (`FRAMEWORK_VERSION` en `backend/core/application.py`, expuesta en `/health` y `/info`): `0.1.0` → `0.2.0-alpha`.

### Notes

- El backend ya es ejecutable end-to-end (`uvicorn backend.main:app --reload` responde en `/`, `/health`, `/live`, `/ready`, `/info`). Sigue sin haber base de datos, autenticación, frontend ejecutable, Docker ni CI/CD reales — llegan en Sprints posteriores (ver `docs/roadmap/ROADMAP.md`, Versión 1 en adelante).
- Sprint 2.2 es exclusivamente infraestructura abstracta: contratos y clases base, sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, storage ni scheduler reales).

[Unreleased]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.5.0-alpha...HEAD
[0.5.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.4.0-alpha...v0.5.0-alpha
[0.4.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.3.0-alpha...v0.4.0-alpha
[0.3.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/main...v0.2.0-alpha
