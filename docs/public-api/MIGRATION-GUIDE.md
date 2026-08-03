# Guía de Migración — TEAF

Cómo migrar código que importa `backend.*` directamente hacia `teaf.*`, y qué esperar cuando `PUBLIC_API_VERSION` suba de versión MAJOR en el futuro.

## 1. Antes de este Sprint

Antes de Sprint 2.5.1 (v0.6.1-alpha) **no existía ninguna API pública** — `teaf/` no existía, y todo el código de ejemplo de los Sprints 2.1-2.6 (incluidos los tests del propio framework) importaba `backend.*` directamente, porque no había otra opción. Eso es normal y correcto para código *dentro* de este repositorio (`backend/`, `tests/`) — sigue siéndolo (ver [IMPORT-GUIDE.md](IMPORT-GUIDE.md), sección 1: `backend.*` es válido dentro del repositorio, nunca fuera).

Esta guía aplica a **cualquier código externo** que haya empezado a construirse contra TEAF antes de este Sprint apoyándose en `backend.*` (por ejemplo, un prototipo propio, o los `examples/` de un Sprint anterior a este) — a partir de v0.6.1-alpha, ese código debe migrar a `teaf.*`.

## 2. Tabla de equivalencia

| Import antiguo (`backend.*`, privado) | Import nuevo (`teaf`, público) |
|---|---|
| `from backend.core.application import create_app` | `from teaf import Application` — luego `Application()` en vez de `create_app()` |
| `from backend.core.application import FRAMEWORK_VERSION` | `from teaf import Version` — luego `Version.framework` |
| `from backend.runtime.runtime import Runtime` | `from teaf import Runtime` |
| `from backend.sdk.module_base import ModuleBase` | `from teaf import Module` (o `ModuleBase`, mismo objeto) |
| `from backend.sdk.builder import ModuleBuilder` | `from teaf import ModuleBuilder` |
| `from backend.sdk.context import ModuleContext` | `from teaf import ModuleContext` |
| `from backend.sdk.manifest import ModuleManifest` | `from teaf import ModuleManifest` |
| `from backend.sdk.enums import ModuleCategory` | `from teaf import ModuleCategory` |
| `from backend.runtime.container import ServiceContainer` | `from teaf import ServiceContainer` |
| `from backend.runtime.container import Lifetime` | `from teaf import Lifetime` |
| `from backend.runtime.event_bus import EventBus` | `from teaf import EventBus` |
| `from backend.runtime.event_bus import Event` | `from teaf import Event` |
| `from backend.runtime.capabilities.registry import CapabilityRegistry` | `from teaf import CapabilityRegistry` |
| `from backend.runtime.capabilities.enums import CapabilityCategory` | `from teaf import CapabilityCategory` |
| `from backend.runtime.capabilities.enums import CapabilityHealth` | `from teaf import Health` |
| `from backend.core.registry import ModuleRegistry` | `from teaf import ModuleRegistry` |
| `from backend.config.settings import Settings, get_settings` | `from teaf import Configuration, get_configuration` |

## 3. Ejemplo completo de migración

**Antes** (privado — dejará de funcionar como API soportada):

```python
from backend.core.application import create_app
from backend.sdk.builder import ModuleBuilder
from backend.sdk.module_base import ModuleBase

app = create_app()
```

**Después** (público — v0.6.1-alpha en adelante):

```python
from teaf import Application, Module, ModuleBuilder

app = Application()
```

Nota el segundo cambio, no solo mecánico: `create_app()` devolvía un `FastAPI` sin envolver; `Application()` devuelve la fachada — usa `app.asgi` si de verdad necesitas el objeto `FastAPI` subyacente (por ejemplo, para montar un router adicional), y `app.runtime`/`app.version` para lo que antes exigía importar `Runtime`/`FRAMEWORK_VERSION` por separado.

## 4. Si un símbolo que necesitas no está en `teaf`

No hagas `from backend.xxx import Yyy` como solución temporal. En su lugar:

1. Verifica en [PUBLIC-API.md](PUBLIC-API.md) si existe un equivalente con otro nombre (por ejemplo, `Health` en vez de `CapabilityHealth`).
2. Si genuinamente falta, es una laguna de la API pública — repórtalo para que se añada a la fachada correspondiente de `teaf/` (ver [PACKAGE-STRUCTURE.md](PACKAGE-STRUCTURE.md)) en un Sprint futuro, en vez de importar `backend.*` directamente.

## 5. Cuando `PUBLIC_API_VERSION` suba de MAJOR

Todavía no ha ocurrido (`PUBLIC_API_VERSION = "1.0.0"`, ver [VERSIONING.md](VERSIONING.md)). Cuando ocurra, esta sección se ampliará con la tabla de cambios incompatibles concretos de esa versión — mismo criterio que ya sigue `CHANGELOG.md` para `FRAMEWORK_VERSION` (Keep a Changelog + SemVer), aplicado específicamente a los símbolos de `teaf/__init__.py`.
