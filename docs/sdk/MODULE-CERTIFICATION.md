# Module Certification — TEAF

`ModuleCertification` (`teaf/_internal/sdk/certification.py`) certifica que un módulo cumple `ModuleSpecification v1` — un nivel más estricto que simplemente poder registrarse en un `Runtime`. Ver visión general en [SDK.md](SDK.md) y las reglas subyacentes en [MODULE-SPECIFICATION.md](MODULE-SPECIFICATION.md).

## 1. Uso

```python
from teaf._internal.sdk.certification import ModuleCertification

result = ModuleCertification().certify(my_module)

result.certified   # bool — True solo si las 8 verificaciones pasan
result.checks       # {"specification": True, "manifest": True, ..., "documentation": False}
result.errors         # tuple[str, ...] — detalle de qué falló
result.as_dict()        # forma serializable (JSON)
```

## 2. Las ocho verificaciones

| Verificación | Qué comprueba | Fuente |
|---|---|---|
| `specification` | El manifiesto pasa `ModuleValidator.validate()` en su totalidad. | `ModuleValidator` |
| `manifest` | Sin errores de metadata (id/nombre/versión con forma válida). | `errors_by_section("metadata")` |
| `metadata` | Igual que `manifest` — mismo origen, nombre distinto por claridad de reporte. | `errors_by_section("metadata")` |
| `capabilities` | Sin capacidades con `id` duplicado. | `errors_by_section("capabilities")` |
| `dependencies` | Sin auto-dependencia ni dependencia duplicada. | `errors_by_section("dependencies")` |
| `version` | La versión declarada tiene forma semver válida. | `errors_by_section("metadata")` |
| `health` | Sin healthchecks con nombre vacío o duplicado. | `errors_by_section("health")` |
| `documentation` | `descriptor.documentation` no está vacío. | Exclusivo de certificación — más estricto que `ModuleValidator` |

`certified = all(checks.values())`. Nota que `manifest`, `metadata` y `version` comparten la misma fuente (`errors_by_section("metadata")`) — no son verificaciones algorítmicamente independientes, sino tres ángulos de reporte sobre la misma sección, nombrados así porque `ModuleSpecification v1` los distingue como secciones separadas del contrato (ver [MODULE-SPECIFICATION.md, sección 1](MODULE-SPECIFICATION.md#1-las-diez-secciones)).

## 3. Por qué `documentation` es más estricta que `ModuleValidator`

`ModuleValidator` no exige `documentation` — un módulo sin ella es perfectamente válido para registrarse en un `Runtime` de desarrollo. `ModuleCertification` sí la exige: es la barra para *distribuir* un módulo (un futuro registro de paquetes, un marketplace de módulos — ver [ROADMAP.md](../roadmap/ROADMAP.md), Versión 5), donde la ausencia de documentación es un defecto real, no un detalle opcional.

```python
result = ModuleCertification().certify(undocumented_module)
result.checks["documentation"]  # False
result.errors  # (..., "documentation: falta 'documentation' — requerida para certificar.")
```

## 4. Relación con `ModuleValidator` (sin duplicar reglas)

`ModuleCertification` nunca reimplementa una regla de validación — llama a `ModuleValidator.validate()` una vez y a `errors_by_section()` para agrupar el resultado por sección. Añadir una verificación de certificación nueva casi siempre significa: (a) si la regla ya existe en `ModuleValidator`, mapear una nueva entrada de `checks` a la sección correspondiente; (b) si es exclusiva de certificación (como `documentation`), añadir la comprobación directamente en `certify()`, documentando por qué es más estricta que el validador base.

## 5. Buenas prácticas

- **No confundas "válido" con "certificado"** — un módulo puede registrarse y funcionar en un `Runtime` sin estar certificado; certificación es una barra de calidad adicional, no un requisito de arranque.
- **Revisa siempre `result.errors`, no solo `result.certified`** — el booleano te dice si pasó, la lista te dice exactamente qué corregir.
- **`ModuleCertification.describe_sections()`** devuelve las ocho claves de `checks` en orden — útil para renderizar un checklist sin hardcodear los nombres en un consumidor externo.
