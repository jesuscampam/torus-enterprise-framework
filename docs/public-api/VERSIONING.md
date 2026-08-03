# Versionado — TEAF

Cinco números de versión independientes, cada uno respondiendo una pregunta de compatibilidad distinta. Todos viven en `teaf.version` (ver `teaf/version.py`) — el único punto de verdad público; nunca se leen literales de versión de otro sitio.

## 1. Los cinco números

| Constante | Responde a | Origen (`backend/`) | Valor actual |
|---|---|---|---|
| `FRAMEWORK_VERSION` | ¿Qué release de TEAF es este? | `backend/core/application.py` | `0.6.1-alpha` |
| `SDK_VERSION` | ¿Qué versión del Module SDK usa un autor de módulos? | `backend/sdk/__init__.py` | `1.0.0` |
| `RUNTIME_VERSION` | ¿Qué versión de la Runtime API consume el SDK? | `backend/runtime/__init__.py` | `1.0.0` |
| `MODULE_SPEC_VERSION` | ¿Qué forma debe tener un `ModuleManifest` válido? | `backend/sdk/specification.py` (`SPEC_VERSION`) | `1.0` |
| `PUBLIC_API_VERSION` | ¿Qué versión de la superficie `teaf.*` es esta? | `teaf/version.py` (nace aquí) | `1.0.0` |

```python
from teaf import Version

Version.framework     # "0.6.1-alpha"
Version.sdk            # "1.0.0"
Version.runtime          # "1.0.0"
Version.module_spec        # "1.0"
Version.public_api           # "1.0.0"
Version.as_dict()              # los cinco, como dict serializable
```

`teaf.Version` es la instancia ya construida (`CURRENT_VERSION` en `teaf/version.py`), no la clase — se consume directamente, nunca se vuelve a instanciar.

## 2. Por qué cinco, y no solo `FRAMEWORK_VERSION`

Cada número evoluciona a un ritmo distinto y protege a un consumidor distinto:

- Un **módulo** (`Module`/`ModuleBase`) declara `sdk_compatibility` contra `SDK_VERSION` — puede seguir siendo válido durante varias versiones de `FRAMEWORK_VERSION` si el SDK no cambió de forma incompatible.
- Un **manifiesto** (`ModuleManifest`) es válido contra `MODULE_SPEC_VERSION` — la forma de un manifiesto puede mantenerse estable aunque el SDK gane nuevas utilidades (`ModuleInspector`, `ModuleCertification`, ...).
- Un **consumidor externo** de `teaf.*` solo necesita que `PUBLIC_API_VERSION` no haya subido de MAJOR — nunca necesita saber qué versión interna de `backend/runtime/` hay detrás.
- `FRAMEWORK_VERSION` es la única que un humano ve en `CHANGELOG.md` y en los tags de Git — las otras cuatro son metadata de compatibilidad, no releases independientes.

## 3. Reglas de compatibilidad actuales

| Compatibilidad | Regla vigente |
|---|---|
| Runtime API | `v1` (`RUNTIME_VERSION = "1.0.0"`) — sin cambios incompatibles todavía. |
| SDK | `v1` (`SDK_VERSION = "1.0.0"`) — sin cambios incompatibles todavía. |
| Module Specification | `v1` (`MODULE_SPEC_VERSION = "1.0"`) — las diez secciones fijadas en Sprint 2.5 (ver [MODULE-SPECIFICATION.md](../sdk/MODULE-SPECIFICATION.md)). |
| Public API | `v1` (`PUBLIC_API_VERSION = "1.0.0"`) — los símbolos de `teaf/__init__.py` fijados en este Sprint (ver [PUBLIC-API.md](PUBLIC-API.md)). |

Un manifiesto declara compatibilidad con una constraint (`">=1.0"`, `"~=1.2"`, `"1.0.0"`...) contra `RUNTIME_VERSION`/`SDK_VERSION` — exactamente el mismo mecanismo que ya usa `ModuleBase._check_compatibility` internamente (`backend/sdk/module_base.py`) para `runtime_compatibility`/`sdk_compatibility` en cada `bootstrap()`.

## 4. `is_compatible()`

Una utilidad pública, independiente del ciclo de vida de un módulo, para que herramientas externas verifiquen compatibilidad antes de actuar (por ejemplo, antes de instalar una integración o mostrar una advertencia):

```python
from teaf.version import is_compatible

is_compatible("0.6.1-alpha", ">=0.5")   # True
is_compatible("0.6.1-alpha", ">=0.7")   # False
is_compatible("1.0.0", "~=1.2")         # False — no es compatible dentro de la misma minor
```

Acepta `"*"`/`""` (cualquier versión), un número exacto, o un operador explícito (`>=`, `<=`, `~=`, `>`, `<`). Una constraint con forma no reconocida se considera satisfecha — permisivo por diseño, mismo criterio que el comparador interno del SDK.

## 5. Relación con el Versionado Semántico del framework

`FRAMEWORK_VERSION` sigue [GIT-STANDARD.md, sección 6](../standards/GIT-STANDARD.md#6-versionado-semántico-semver) (`MAJOR.MINOR.PATCH`, con sufijo `-alpha` mientras el framework no alcanza V1 del roadmap). Los otros cuatro números **no** seleccionan el mismo esquema por obligación — cada uno sube solo cuando su propio contrato cambia de forma incompatible, independientemente de cuántas veces suba `FRAMEWORK_VERSION` mientras tanto. Ver [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md) para qué hacer cuando alguno de los cinco sube de MAJOR.
