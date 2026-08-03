# Platform Intelligence — TEAF

Documentación del Sprint 2.4 (Platform Intelligence, v0.4.0-alpha): la capa que permite al Runtime **describirse a sí mismo** — qué capacidades tiene, qué módulos, servicios y plugins están registrados, qué feature flags existen y en qué estado corre — expuesta tanto por HTTP como en proceso. Complementa — no reemplaza — [docs/runtime/RUNTIME.md](../runtime/RUNTIME.md) (Sprint 2.3): todo lo documentado ahí sigue vigente sin cambios de comportamiento.

> Ninguna capacidad de negocio, plugin real ni integración de IA/MCP se conecta en este Sprint. Platform Intelligence es la **infraestructura de introspección** — el "espejo" del Runtime — no una funcionalidad de negocio.

## 1. Por qué existe

Un framework que va a sostener años de aplicaciones (TicketGateway, Portal TORUS, Portal NOC, Inventario TI, IA Empresarial...) necesita poder responder, en cualquier momento y sin documentación desactualizada: *¿qué versión corro? ¿qué módulos están activos? ¿qué puede hacer esta instancia? ¿está lista para IA/MCP?* Platform Intelligence responde estas preguntas leyendo el estado real del `Runtime` en el momento de la consulta — nunca datos simulados ni una fotografía capturada al arrancar.

## 2. Arquitectura

```
backend/runtime/
├── capabilities/                       # Capability Model — ver CAPABILITY-REGISTRY.md
│   ├── enums.py                          # CapabilityCategory, CapabilityStatus, CapabilityHealth
│   ├── metadata.py                        # CapabilityMetadata, Capability
│   ├── builder.py                          # CapabilityBuilder (fluido)
│   ├── registry.py                          # CapabilityRegistry
│   └── provider_registry.py                  # CapabilityProviderRegistry — preparación MCP
├── features/                            # Feature Flags
│   ├── enums.py                           # FeatureGroup, FeatureStatus
│   ├── flag.py                             # FeatureFlag
│   └── manager.py                           # FeatureManager
├── service_discovery.py                 # ServiceDiscovery — consulta de ServiceContainer
├── diagnostics.py                       # RuntimeDiagnostics
├── self_description.py                  # RuntimeSelfDescription
├── manifest.py                          # generate_manifest()/write_manifest() → runtime.manifest.json
├── api.py                               # Runtime API HTTP — ver RUNTIME-API.md
└── runtime.py                           # Runtime — extendido con wrappers + diagnostics()/self_description()

backend/developer/
└── runtime_api.py                       # DeveloperRuntimeAPI — ver DEVELOPER-API.md

backend/contracts/
├── capability_provider.py               # CapabilityProvider — preparación IA/MCP, solo contrato
└── framework_knowledge.py               # FrameworkKnowledgeProvider — preparación IA, solo contrato
```

`Runtime` (Sprint 2.3) se **extiende, no se reemplaza**: gana cuatro atributos compuestos nuevos (`capability_registry`, `feature_manager`, `capability_provider_registry`, `service_discovery`), un conjunto de métodos wrapper (`register_module`, `register_service`, `register_capability`, `load_plugin`, `enable_feature`, y sus contrapartes de baja/eliminación), y dos métodos de consulta (`diagnostics()`, `self_description()`). Todo el código de Sprint 2.3 (`container.py`, `lifecycle.py`, `pipeline.py`, `event_bus.py`, `plugin_loader.py`, etc.) sigue funcionando sin cambios de comportamiento — las pruebas de Sprint 2.3 pasan sin modificación.

**Dependencias declaradas**: igual que el resto de `backend/runtime/`, ningún archivo nuevo importa `backend/contracts/` ni `backend/providers/`. Donde el modelo necesita relacionarse con un contrato futuro (`CapabilityProvider`), se usa un `typing.Protocol` estructural local (`CapabilityProviderLike` en `provider_registry.py`) en vez de un import — ver [CAPABILITY-REGISTRY.md, sección 4](CAPABILITY-REGISTRY.md#4-preparación-para-mcp-capabilityproviderregistry).

## 3. Las cuatro preguntas que responde

| Pregunta | Respondida por |
|---|---|
| ¿Qué **capacidades** tiene esta instancia? | `CapabilityRegistry` — ver [CAPABILITY-REGISTRY.md](CAPABILITY-REGISTRY.md) |
| ¿Qué puedo **consultar por HTTP**? | Runtime API (`GET /runtime/*`) — ver [RUNTIME-API.md](RUNTIME-API.md) |
| ¿Cómo lo consulto **sin HTTP**, desde el mismo proceso? | Developer API (`DeveloperRuntimeAPI`) — ver [DEVELOPER-API.md](DEVELOPER-API.md) |
| ¿Cómo se **describe a sí mismo** el framework? | `RuntimeSelfDescription`, `RuntimeDiagnostics`, `runtime.manifest.json` — ver [SELF-DESCRIBING-RUNTIME.md](SELF-DESCRIBING-RUNTIME.md) |

## 4. Eventos nuevos en el `EventBus`

Todos usan el `EventBus` ya existente desde Sprint 2.3 (pub/sub síncrono, en proceso) — ningún mecanismo de mensajería nuevo. El `Runtime` los publica automáticamente desde sus métodos wrapper:

| Evento | Publicado por |
|---|---|
| `framework.started` / `framework.stopped` | `Runtime.startup()` / `Runtime.shutdown()` (junto a los ya existentes `framework.startup.completed`/`framework.shutdown.completed`, conservados por compatibilidad) |
| `module.registered` / `module.unregistered` | `Runtime.register_module()` / `Runtime.unregister_module()` |
| `service.registered` / `service.removed` / `service.resolved` | `Runtime.register_service()` / `Runtime.remove_service()` / `Runtime.resolve_service()` |
| `capability.registered` / `capability.removed` | `Runtime.register_capability()` / `Runtime.remove_capability()` |
| `plugin.loaded` / `plugin.unloaded` | `Runtime.load_plugin()` / `Runtime.unload_plugin()` |
| `feature.enabled` / `feature.disabled` | `Runtime.enable_feature()` / `Runtime.disable_feature()` |

El `EventBus` ahora retiene, además, un **historial acotado** (`history_limit`, 100 eventos por defecto) consultable con `event_bus.history(limit=...)` — expuesto vía `GET /runtime/events`.

## 5. Buenas prácticas para extender Platform Intelligence

- **Usa siempre los wrappers de `Runtime`** (`register_capability`, `enable_feature`, etc.) en vez de llamar directamente a `runtime.capability_registry.register(...)` — solo los wrappers publican el evento correspondiente.
- **No registres capacidades/feature flags reales todavía** — este Sprint es infraestructura pura; la primera capacidad real la registrará el módulo que la implemente (Database, Security, AI...) cuando deje de ser `contracts_only`.
- **La Runtime API y el Developer API comparten la misma lógica de ensamblado** (`build_*_payload` en `backend/runtime/api.py`) — si necesitas una vista nueva, añade una función `build_*_payload` y expónla en ambos lados, nunca dupliques el ensamblado.
- **`runtime.manifest.json` nunca se versiona** (ver `.gitignore`) — es un artefacto generado en cada arranque real (no en tests), no una fuente de verdad editable a mano.

## 6. Qué NO incluye este Sprint

Sin SQLAlchemy, PostgreSQL, Alembic, JWT, OAuth, Azure SDK, Docker, GitHub Actions, OpenTelemetry real, IA, MCP, Scheduler, Storage ni Notificaciones funcionales. Sin persistencia: capacidades, feature flags, servicios y plugins viven en memoria y se reinician con el proceso. Todo eso llega en Sprints posteriores (ver [ROADMAP.md](../roadmap/ROADMAP.md)).
