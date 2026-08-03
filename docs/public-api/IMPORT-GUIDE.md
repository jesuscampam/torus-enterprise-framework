# Guía de Imports — TEAF

Qué namespaces son públicos y cuáles son privados, y cómo se verifica. Ver [PUBLIC-API.md](PUBLIC-API.md) para el catálogo de símbolos concretos.

## 1. La regla

| Namespace | Estado | Uso permitido |
|---|---|---|
| `teaf` | **Público** | Cualquier consumidor externo, cualquier ejemplo de `examples/`. Único punto de entrada soportado. |
| `backend` (y todo lo que cuelga: `backend.core`, `backend.config`, `backend.runtime`, `backend.sdk`, `backend.contracts`, `backend.providers`, `backend.modules`, `backend.middleware`, `backend.monitoring`, ...) | **Privado** | Solo dentro de este repositorio: las propias fachadas de `teaf/`, y las pruebas de caja blanca del framework (`tests/`) que necesitan verificar la implementación interna. |

```python
# Correcto — cualquier consumidor externo:
from teaf import Application, Module, ModuleBuilder

# Incorrecto — nunca fuera de este repositorio, ni en examples/:
from backend.core.application import create_app
from backend.sdk.module_base import ModuleBase
```

No hay una lista de excepciones: si un símbolo de `backend/` es genuinamente útil para un consumidor externo, la corrección es exponerlo desde la fachada correspondiente de `teaf/` (ver [PACKAGE-STRUCTURE.md](PACKAGE-STRUCTURE.md)) — nunca "solo por esta vez" importar `backend.*` directamente desde fuera.

## 2. Por qué

`backend/` es libre de reorganizarse entre Sprints — mover un archivo, renombrar una clase interna, dividir un módulo — sin que eso rompa a ningún consumidor de `teaf`, siempre que el contrato de `teaf/__init__.py` no cambie (ver `PUBLIC_API_VERSION` en [VERSIONING.md](VERSIONING.md)). Si un consumidor externo importara `backend.sdk.module_base.ModuleBase` directamente, cualquier reorganización interna de `backend/sdk/` sería, de hecho, un cambio incompatible para ese consumidor — exactamente lo que la fachada existe para evitar.

## 3. El verificador de límites

`scripts/check_public_api_boundary.py` analiza estáticamente (vía `ast`, sin ejecutar ningún código) un árbol de archivos `.py` y reporta cualquier `import backend...`/`from backend... import ...` encontrado:

```bash
python scripts/check_public_api_boundary.py examples/
# OK — ningún import de namespace privado ('backend',) encontrado.
```

Se ejecuta hoy sobre `examples/` (ver `tests/unit/test_examples_public_api_only.py`, que lo invoca como parte de la suite de pruebas) — sienta la base para una futura verificación en CI sobre cualquier proyecto externo o plantilla de arranque, sin estar cableado a ningún pipeline todavía (ver Sprint 2.5.1, sección 8).

`teaf/` mismo, y `tests/`, quedan fuera del alcance de este verificador a propósito: ambos necesitan importar `backend.*` para funcionar (son la implementación y sus pruebas de caja blanca, respectivamente) — el límite aplica a *consumidores*, no a este repositorio en su totalidad.

## 4. API de la utilidad

Para quien quiera reutilizarla (por ejemplo, en un test nuevo o un futuro hook de CI):

```python
from pathlib import Path
from scripts.check_public_api_boundary import check_paths, find_forbidden_imports

violations = check_paths([Path("examples/")])
# o, sobre código en memoria:
violations = find_forbidden_imports(source_code, path=Path("virtual.py"))
```

Ambas devuelven una lista de `ImportViolation(path, line, module)` — vacía si no hay infracciones.
