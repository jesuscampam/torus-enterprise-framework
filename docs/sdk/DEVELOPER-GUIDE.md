# Developer Guide — Module SDK (TEAF)

Guía práctica, de punta a punta, para crear un módulo con el SDK: generar el esqueleto, implementarlo, inspeccionarlo, documentarlo, certificarlo y arrancarlo contra un `Runtime`. Ver visión general en [SDK.md](SDK.md); referencia detallada de cada pieza en [MODULE-SPECIFICATION.md](MODULE-SPECIFICATION.md), [MODULE-BUILDER.md](MODULE-BUILDER.md), [MODULE-LIFECYCLE.md](MODULE-LIFECYCLE.md) y [MODULE-CERTIFICATION.md](MODULE-CERTIFICATION.md).

## 1. Generar el esqueleto con `ModuleScaffolder`

Sin CLI en este Sprint — se invoca directamente desde Python (una futura CLI llamará a este mismo servicio):

```python
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.scaffolder import ModuleScaffolder, write_to_disk
from pathlib import Path

scaffold = ModuleScaffolder().scaffold(
    module_id="greeter", name="Greeter", category=ModuleCategory.GENERIC
)
list(scaffold.files)  # ["greeter/__init__.py", "greeter/module.py", "greeter/README.md"]

# Escribir a disco es un paso explícito y separado — nunca automático:
write_to_disk(scaffold, Path("./modules"))
```

`scaffold()` usa `MODULE_TEMPLATES` (`templates.py`) para sugerir capacidades/servicios según la categoría — comentados como TODO en el `module.py` generado, nunca código de negocio real. El archivo generado ya es una subclase válida de `ModuleBase`, lista para completar.

## 2. Implementar el módulo

Completa los hooks que necesites y las capacidades/servicios reales en `get_manifest()`:

```python
class GreeterModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="greeter", name="greeter", display_name="Greeter")
            .with_version("1.0.0")
            .with_description("Saluda a quien se lo pida.")
            .with_documentation("modules/greeter/README.md")
            .add_service(Greeter, lambda c: Greeter())
            .add_capability(id="greeter.hello", name="greeter-hello")
            .build()
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info("greeter_ready")
```

## 3. Inspeccionar antes de registrar con `ModuleInspector`

Útil en tests o en una consola interactiva, sin necesitar un `Runtime`:

```python
from teaf._internal.sdk.inspector import ModuleInspector

inspector = ModuleInspector(GreeterModule())
inspector.describe()       # manifiesto aplanado + estado del lifecycle
inspector.capabilities()   # (ModuleCapability(id="greeter.hello", ...),)
inspector.services()       # (ModuleService(contract=Greeter, ...),)
```

## 4. Generar documentación con `ModuleDocumentationGenerator`

```python
from teaf._internal.sdk.documentation_generator import ModuleDocumentationGenerator

doc = ModuleDocumentationGenerator().generate(GreeterModule().get_manifest())
Path("modules/greeter/GREETER.md").write_text(doc, encoding="utf-8")  # escribirlo es cosa tuya
```

El generador **nunca** escribe archivos por sí mismo (ver Sprint 2.5, ítem 14) — devuelve un `str` Markdown; tú decides dónde persistirlo.

## 5. Certificar con `ModuleCertification`

Antes de considerar el módulo listo para compartirse (marketplace de módulos, un Sprint futuro — ver [ROADMAP.md](../roadmap/ROADMAP.md)):

```python
from teaf._internal.sdk.certification import ModuleCertification

result = ModuleCertification().certify(GreeterModule())
if not result.certified:
    raise SystemExit(f"No certificado: {result.errors}")
```

## 6. Arrancar contra un `Runtime` real

```python
import asyncio
from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.context import ModuleContext

async def main() -> None:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.5.0-alpha")
    await runtime.startup()

    module = GreeterModule()
    context = ModuleContext(runtime=runtime, module_id="greeter", configuration={})
    await module.bootstrap(context)
    # runtime.container.is_registered(Greeter) es True
    # runtime.capability_registry.exists("greeter.hello") es True
    # runtime.modules incluye el descriptor de "greeter"

    ...  # el módulo está READY

    await module.shutdown(context)
    await runtime.shutdown()

asyncio.run(main())
```

## 7. Diagnosticar un fallo

Cada excepción del SDK indica exactamente qué salió mal y en qué etapa (ver [MODULE-LIFECYCLE.md, sección 3](MODULE-LIFECYCLE.md#3-bootstrap--el-orden-exacto)):

| Excepción | Causa típica | Qué revisar |
|---|---|---|
| `ModuleValidationException` | El manifiesto no cumple `ModuleSpecification v1`. | `ModuleValidator().validate(manifest).errors` |
| `ModuleCompatibilityException` | `runtime_compatibility`/`sdk_compatibility` no se cumplen. | La versión real del `Runtime`/SDK contra el constraint declarado. |
| `ModuleRegistrationException` | El módulo ya estaba registrado, o una capacidad colisiona con otra. | `runtime.modules` / `runtime.capability_registry.list()` |
| `ModuleLifecycleException` | Un hook lanzó una excepción. | `module.lifecycle.state` (será `FAILED`) y el mensaje, que nombra el hook y la etapa. |
| `ModuleDependencyException` | Ciclo o conflicto de versión entre varios módulos (`ModuleDependencyResolver`). | `resolver.detect_cycle()` / `resolver.detect_conflicts()` |

## 8. Checklist antes de dar por terminado un módulo

- [ ] `get_manifest()` no tiene efectos secundarios y es determinista.
- [ ] Todos los servicios declarados tienen `description`/`tags` útiles (no solo el contrato).
- [ ] `documentation` apunta a un archivo real, no un placeholder.
- [ ] `ModuleValidator().validate(manifest).valid` es `True`.
- [ ] `ModuleCertification().certify(module).certified` es `True`.
- [ ] `bootstrap()`/`shutdown()` probados contra un `Runtime` real en un test (no solo `get_manifest()` en aislamiento).
- [ ] Ningún hook llama directamente a `ServiceContainer`/`CapabilityRegistry` — todo pasa por el manifiesto y los binders.
