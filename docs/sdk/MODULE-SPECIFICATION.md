# Module Specification v1 — TEAF

`ModuleSpecification` (`teaf/_internal/sdk/specification.py`) es el contrato formal que todo módulo TEAF debe cumplir: diez secciones obligatorias, declaradas — no implementadas — en `ModuleSpecificationSection`. Las reglas concretas que comprueban cada sección viven en `ModuleValidator` (`teaf/_internal/sdk/validator.py`). Separar "qué debe cumplirse" de "cómo se comprueba" es lo que permite versionar la especificación (`SPEC_VERSION`) sin tocar el motor de validación. Ver visión general en [SDK.md](SDK.md).

## 1. Las diez secciones

| Sección | Qué describe | Dónde vive en `ModuleManifest` |
|---|---|---|
| Metadata | Id, nombre, versión, autor, categoría | `manifest.descriptor` |
| Lifecycle | Hooks del ciclo de vida | `ModuleBase` (no forma parte del manifiesto) |
| Dependencies | Otros módulos requeridos | `manifest.dependencies` |
| Capabilities | Qué aporta el módulo | `manifest.capabilities` |
| Configuration | Qué configuración necesita | `manifest.configuration` |
| Services | Qué registra en el `ServiceContainer` | `manifest.services` |
| Health | Verificaciones de salud declaradas | `manifest.health_checks` |
| Documentation | Enlace a documentación externa | `manifest.descriptor.documentation` |
| Packaging | Compatibilidad Runtime/SDK | `manifest.runtime_compatibility` / `manifest.sdk_compatibility` |
| Validation Rules | Las propias reglas de `ModuleValidator` | — (metasección) |

```python
from teaf._internal.sdk.specification import CURRENT_SPECIFICATION

CURRENT_SPECIFICATION.version    # "1.0"
CURRENT_SPECIFICATION.describe() # {"version": "1.0", "sections": [...10 nombres...]}
```

## 2. `ModuleValidator` — el motor

`ModuleValidator.validate(manifest)` ejecuta un método `_check_*` por sección (salvo "Lifecycle" y "Validation Rules", que no aplican a un manifiesto estático) y agrega todos los errores en un `ModuleValidationResult`:

```python
result = ModuleValidator().validate(manifest)
result.valid    # bool
result.errors   # tuple[str, ...], cada uno con el prefijo de su sección: "metadata: ...", "capabilities: ...", ...
```

`validate_or_raise(manifest)` hace lo mismo pero lanza `ModuleValidationException` (con todos los errores unidos) si `valid` es `False` — es lo que usa `ModuleBase.bootstrap()` internamente, nunca `validate()` a secas.

### Reglas por sección

| Sección | Regla |
|---|---|
| Metadata | `id` es un slug en minúsculas (`^[a-z][a-z0-9_.-]*$`); `name`/`display_name` no vacíos; `version` es semver (`X.Y.Z` o `X.Y.Z-prerelease`). |
| Dependencies | Un módulo no puede depender de sí mismo; sin `module_id` duplicado. |
| Capabilities | Sin `id` de capacidad duplicado dentro del mismo manifiesto. |
| Configuration | Sin clave duplicada. |
| Services | Sin `contract` (tipo) duplicado. |
| Health | Todo healthcheck tiene `name` no vacío; sin nombre duplicado. |
| Packaging | `runtime_compatibility`/`sdk_compatibility` cumplen `(\*|(==|>=|<=|~=|>|<)?\d+\.\d+(\.\d+)?)` — ver [MODULE-LIFECYCLE.md, sección 4](MODULE-LIFECYCLE.md#4-compatibilidad-runtimesdk). |

### `errors_by_section` — depuración dirigida

```python
ModuleValidator().errors_by_section(manifest)
# {"metadata": ("metadata: 'id' inválido...",), "capabilities": ("capabilities: id duplicado...",)}
```

Agrupa los errores de `validate()` por su prefijo — usado por `ModuleCertification` ([MODULE-CERTIFICATION.md](MODULE-CERTIFICATION.md)) para reportar certificación sección por sección sin reimplementar ninguna regla.

## 3. Lo que el validador **no** hace

- No resuelve dependencias entre varios módulos (ciclos, conflictos de versión) — eso es `ModuleDependencyResolver`, una preocupación multi-manifiesto distinta de validar uno solo.
- No verifica compatibilidad contra un `Runtime` en ejecución — solo que `runtime_compatibility`/`sdk_compatibility` tengan una forma reconocible. La comprobación real contra versiones vivas ocurre en `ModuleBase._check_compatibility` durante `bootstrap()`.
- No valida semántica de negocio — un módulo puede ser válido y seguir siendo un mal diseño; la especificación es estructural, no de calidad.

## 4. Buenas prácticas

- **Llama siempre a `validate_or_raise`, no a `validate`**, salvo que quieras inspeccionar errores sin abortar (p. ej. en una herramienta de desarrollador como `ModuleCertification`).
- **Trata los prefijos de `errors_by_section` como estables** — “metadata”, “dependencies”, “capabilities”, “configuration”, “services”, “health”, “packaging” — cualquier herramienta que los consuma puede depender de esos nombres exactos.
- **Una especificación `v2` futura se añade, no se sobrescribe**: crea una nueva `ModuleSpecification(version="2.0", sections=(...))` y un `ModuleValidator` (o modo) que la use, sin romper `v1`.
