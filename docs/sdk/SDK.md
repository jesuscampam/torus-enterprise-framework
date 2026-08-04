# Module SDK — TEAF

Documentación del Sprint 2.5 (Developer Platform, v0.5.0-alpha): el SDK oficial para construir módulos de TEAF, apoyado en todo lo que Platform Intelligence (Sprint 2.4) y el Runtime (Sprint 2.3) ya ofrecen. Vive en `teaf/_internal/sdk/`. Complementa — no reemplaza — [docs/runtime/RUNTIME.md](../runtime/RUNTIME.md) y [docs/platform/PLATFORM-INTELLIGENCE.md](../platform/PLATFORM-INTELLIGENCE.md).

> Ningún módulo real (Database, Security, AI...) se construye con este SDK en este Sprint. Es infraestructura de autoría — pensada para que, cuando esos módulos se implementen, hereden de `ModuleBase` en vez de cablearse a mano contra el Runtime.

## 1. La promesa central

> Un desarrollador crea un módulo completo heredando únicamente de `ModuleBase`. Toda la infraestructura se registra automáticamente en el Runtime.

```python
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase

class GreeterModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="greeter", name="greeter", display_name="Greeter")
            .add_service(Greeter, lambda c: Greeter())
            .add_capability(id="greeter.hello", name="greeter-hello")
            .build()
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info("greeter_ready")
```

```python
module = GreeterModule()
await module.bootstrap(ModuleContext(runtime=runtime, module_id="greeter"))
# El servicio Greeter y la capacidad greeter.hello ya están registrados en
# runtime.container / runtime.capability_registry — sin una sola llamada manual.
```

> Esa llamada a `bootstrap()` es lo que ocurre *por dentro* — el nivel de detalle que necesita quien escribe un módulo. Un consumidor de una `Application` completa nunca la invoca directamente: le basta con `Application(modules=[GreeterModule()])` (o `Application().add_module(GreeterModule())`), y TEAF llama a `bootstrap()` automáticamente cuando arranca el ciclo de vida ASGI — ver ["Registrar módulos"](../public-api/PUBLIC-API.md#3-registrar-módulos-module-registration-api-sprint-263) en PUBLIC-API.md (Sprint 2.6.3).

## 2. Arquitectura

```
teaf/_internal/sdk/
├── enums.py                    # ModuleCategory
├── exceptions.py                 # 5 excepciones del SDK
├── descriptor.py                   # ModuleDescriptor (metadata de autoría)
├── configuration.py                  # ModuleConfiguration
├── health.py                           # ModuleHealth
├── capability.py                         # ModuleCapability (declaración ligera)
├── service.py                              # ModuleService (declaración ligera)
├── dependency.py                             # ModuleDependency
├── lifecycle.py                                # ModuleLifecycleState, ModuleLifecycle
├── manifest.py                                   # ModuleManifest
├── specification.py                                # ModuleSpecification v1
├── builder.py                                        # ModuleBuilder (fluido)
├── validator.py                                        # ModuleValidator
├── dependency_resolver.py                                # ModuleDependencyResolver
├── service_binder.py                                       # ServiceBinder
├── capability_binder.py                                      # CapabilityBinder
├── context.py                                                  # ModuleContext
├── module_base.py                                                # ModuleBase (orquestador)
├── inspector.py                                                    # ModuleInspector
├── templates.py                                                      # MODULE_TEMPLATES (7 categorías)
├── scaffolder.py                                                       # ModuleScaffolder
├── documentation_generator.py                                            # ModuleDocumentationGenerator
└── certification.py                                                        # ModuleCertification
```

**Dependencias declaradas**: `teaf/_internal/sdk/` importa de `teaf/_internal/core/` y `teaf/_internal/runtime/` — a diferencia de `teaf/_internal/runtime/`, que nunca depende de `contracts/`/`providers/`, el SDK **sí** depende del Runtime: es la capa que se apoya en él para ofrecer autoría de alto nivel. Ningún archivo de `teaf/_internal/runtime/` ni `teaf/_internal/core/` importa `teaf/_internal/sdk/` — la dependencia va en un solo sentido.

## 3. Los tres roles de cada pieza

| Rol | Piezas | Responsabilidad |
|---|---|---|
| **Describir** | `descriptor.py`, `capability.py`, `service.py`, `dependency.py`, `configuration.py`, `health.py`, `manifest.py`, `builder.py` | Declarar qué es un módulo y qué aporta — sin tocar el Runtime. |
| **Validar** | `specification.py`, `validator.py`, `dependency_resolver.py` | Comprobar que lo declarado es coherente, antes de registrar nada. |
| **Registrar y ejecutar** | `service_binder.py`, `capability_binder.py`, `context.py`, `module_base.py`, `lifecycle.py` | Traducir lo declarado en llamadas reales al `Runtime` y ejecutar el ciclo de vida. |

Las tres piezas restantes — `inspector.py`, `templates.py`/`scaffolder.py`, `documentation_generator.py`, `certification.py` — son **herramientas de desarrollador**, no parte del camino crítico de `bootstrap()`: ver [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md).

## 4. Documentos relacionados

| Documento | Contenido |
|---|---|
| [MODULE-SPECIFICATION.md](MODULE-SPECIFICATION.md) | Las diez secciones de `ModuleSpecification v1` y las reglas de `ModuleValidator`. |
| [MODULE-BUILDER.md](MODULE-BUILDER.md) | `ModuleBuilder` — API completa y ejemplos de las 7 categorías. |
| [MODULE-LIFECYCLE.md](MODULE-LIFECYCLE.md) | Los ocho estados de `ModuleLifecycle`, los siete hooks y el orden exacto de `bootstrap()`/`shutdown()`. |
| [MODULE-CERTIFICATION.md](MODULE-CERTIFICATION.md) | `ModuleCertification` — las ocho verificaciones y cómo interpretarlas. |
| [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md) | Guía práctica: crear, inspeccionar, documentar y certificar un módulo paso a paso. |

## 5. Buenas prácticas

- **Nunca llames a `ServiceContainer.register_*` ni a `CapabilityRegistry.register` directamente desde un módulo** — declara el servicio/capacidad en el manifiesto (`ModuleBuilder.add_service`/`add_capability`) y deja que `ServiceBinder`/`CapabilityBinder` lo hagan durante `bootstrap()`.
- **No sobrescribas `bootstrap()` ni `shutdown()`** — son el contrato fijo del SDK; personaliza el comportamiento sobrescribiendo los siete hooks (`initialize`, `configure`, `register`, `start`, `ready`, `stop`, `dispose`).
- **`get_manifest()` debe ser puro** — sin efectos secundarios, sin tocar el Runtime; se llama en cada `bootstrap()` y también desde `ModuleInspector`/`ModuleCertification` sin que eso registre nada.
- **Versiona `sdk_compatibility` con criterio** — declara el rango real que tu módulo soporta, no `"*"` por comodidad; `ModuleBase._check_compatibility` lo hace cumplir antes de registrar nada.

## 6. Qué NO incluye este Sprint

Sin CLI, sin generación de proyectos completos, sin persistencia de módulos, sin Database/Security/Storage/Scheduler/OpenTelemetry/Azure/MCP/AI reales. `ModuleScaffolder` genera esqueletos en memoria (opcionalmente escritos a disco vía `write_to_disk`), nunca invocado desde una interfaz de línea de comandos. Todo eso llega en Sprints posteriores (ver [ROADMAP.md](../roadmap/ROADMAP.md)).
