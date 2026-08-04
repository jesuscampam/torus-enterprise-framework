# API Pública — TEAF

Documentación del Sprint 2.5.1 (Public SDK & Packaging, v0.6.1-alpha): `teaf/` es, desde este Sprint, la **única** superficie que un consumidor externo de TEAF debe importar. Complementa — no reemplaza — [docs/sdk/SDK.md](../sdk/SDK.md) (que documenta el Module SDK *por dentro*, para quien trabaja en el propio framework) y [docs/runtime/RUNTIME.md](../runtime/RUNTIME.md).

> Este Sprint no añade capacidades nuevas al Runtime ni módulos nuevos — es exclusivamente empaquetado y experiencia de desarrollador sobre todo lo construido en los Sprints 2.1-2.6.

## 1. Instalación

```bash
pip install -e ../teaf-framework   # desde un proyecto externo
# o, dentro de este repositorio:
pip install -e .
```

Ver [`pyproject.toml`](../../pyproject.toml) — sección `[project]`.

## 2. Uso mínimo

```python
from teaf import Application

app = Application()
```

```bash
uvicorn app:app   # si lo anterior vive en app.py
```

Ver [`examples/`](../../examples/) para tres ejemplos completos y ejecutables.

## 3. Los catorce símbolos principales

| Símbolo | Qué es | Fachada (`teaf/`) | Envuelve (`teaf/_internal/`) |
|---|---|---|---|
| `Application` | Construye y sirve una aplicación TEAF completa; callable ASGI. | `application.py` | `teaf._internal.core.application.create_app` |
| `Runtime` | Orquestador de ciclo de vida: contenedor, capacidades, eventos, módulos. | `runtime.py` | `teaf._internal.runtime.runtime.Runtime` |
| `Module` | Alias corto de `ModuleBase` — hereda de él para escribir un módulo. | `modules.py` | `teaf._internal.sdk.module_base.ModuleBase` |
| `ModuleBase` | Mismo objeto que `Module`, nombre explícito del SDK. | `modules.py` | `teaf._internal.sdk.module_base.ModuleBase` |
| `ModuleBuilder` | Construcción fluida de un `ModuleManifest`. | `modules.py` | `teaf._internal.sdk.builder.ModuleBuilder` |
| `ModuleContext` | Contexto pasado a cada hook de un módulo (`runtime`, `logger`, `configuration`). | `modules.py` | `teaf._internal.sdk.context.ModuleContext` |
| `ModuleManifest` | El manifiesto completo que describe un módulo. | `modules.py` | `teaf._internal.sdk.manifest.ModuleManifest` |
| `ServiceContainer` | Contenedor de inyección de dependencias por contrato. | `services.py` | `teaf._internal.runtime.container.ServiceContainer` |
| `EventBus` | Publicación/suscripción interna del framework. | `events.py` | `teaf._internal.runtime.event_bus.EventBus` |
| `CapabilityRegistry` | Inventario de capacidades registradas. | `capabilities.py` | `teaf._internal.runtime.capabilities.registry.CapabilityRegistry` |
| `ModuleRegistry` | Inventario de módulos registrados (introspección). | `modules.py` | `teaf._internal.core.registry.ModuleRegistry` |
| `Health` | Vocabulario de salud (`UNKNOWN`/`HEALTHY`/`DEGRADED`/`UNHEALTHY`). | `health.py` | `teaf._internal.runtime.capabilities.enums.CapabilityHealth` |
| `Configuration` | Configuración tipada por entorno. | `configuration.py` | `teaf._internal.config.settings.Settings` |
| `Version` | Fotografía inmutable de los cinco números de versión de TEAF. | `version.py` | agrega varios (ver [VERSIONING.md](VERSIONING.md)) |

## 4. Símbolos compañeros

Sin estos, algunos de los catorce anteriores no se pueden usar sin recurrir a `teaf._internal.*` — se exportan por necesidad práctica, no por descuido (ver [PACKAGE-STRUCTURE.md](PACKAGE-STRUCTURE.md)):

| Símbolo | Necesario para |
|---|---|
| `Lifetime` | `ModuleBuilder.add_service(..., lifetime=Lifetime.SCOPED)` |
| `Event` | `EventBus.publish(Event(name="algo"))` |
| `CapabilityCategory` | `ModuleBuilder.add_capability(..., category=CapabilityCategory.DATABASE)` |
| `ModuleCategory` | `ModuleBuilder.with_category(ModuleCategory.INTEGRATION)` |
| `get_configuration` | Función homóloga de `Configuration`/`get_settings()`. |

## 5. Qué NO expone `teaf`

Ninguna clase de `teaf._internal.core`, `teaf._internal.runtime` (más allá de `Runtime`/`ServiceContainer`/`EventBus`/`CapabilityRegistry`), `teaf._internal.sdk` (más allá de lo listado arriba), `teaf._internal.contracts`, `teaf._internal.providers` o `teaf._internal.modules` — ver [IMPORT-GUIDE.md](IMPORT-GUIDE.md) para la regla completa y cómo se verifica. En particular, no se exponen: `DatabaseModule` ni ningún módulo real (Sprint 2.6 sigue siendo opt-in, ni siquiera se importa desde `teaf/`), `DeveloperRuntimeAPI`, ni ninguna clase de infraestructura de introspección avanzada (`ModuleInspector`, `ModuleCertification`, `ModuleScaffolder`) — esas siguen siendo herramientas internas de desarrollo del propio framework, no parte de la superficie de autoría de un consumidor externo.

## 6. Documentos relacionados

| Documento | Contenido |
|---|---|
| [PACKAGE-STRUCTURE.md](PACKAGE-STRUCTURE.md) | Qué archivo de `teaf/` contiene qué, y por qué está separado así. |
| [IMPORT-GUIDE.md](IMPORT-GUIDE.md) | Namespaces públicos/privados, el verificador de límites. |
| [VERSIONING.md](VERSIONING.md) | Los cinco números de versión y las reglas de compatibilidad. |
| [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md) | Tabla de equivalencia `teaf._internal.*` → `teaf.*`. |
