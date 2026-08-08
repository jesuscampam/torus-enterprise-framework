# Guía de Imports — TEAF

Qué namespaces son públicos y cuáles son privados, y cómo se verifica. Ver [PUBLIC-API.md](PUBLIC-API.md) para el catálogo de símbolos concretos.

## 1. La regla

| Namespace | Estado | Uso permitido |
|---|---|---|
| `teaf` | **Público** | Cualquier consumidor externo, cualquier ejemplo de `examples/`. Único punto de entrada soportado. |
| `teaf.security`, `teaf.observability`, `teaf.api` (y el resto de fachadas de `teaf/`: `application`, `runtime`, `modules`, `services`, `events`, `configuration`, `capabilities`, `health`, `version`) | **Público** | Igual que `teaf`: cada una agrupa una plataforma o una capa, y todo lo que exportan se reexporta también desde `teaf` — `from teaf import ApiGateway` y `from teaf.api import ApiGateway` son equivalentes. |
| `teaf._internal` (y todo lo que cuelga: `teaf._internal.core`, `teaf._internal.config`, `teaf._internal.runtime`, `teaf._internal.sdk`, `teaf._internal.contracts`, `teaf._internal.providers`, `teaf._internal.modules`, `teaf._internal.middleware`, `teaf._internal.monitoring`, ...) | **Privado** | Solo dentro de este repositorio: las propias fachadas de `teaf/`, y las pruebas de caja blanca del framework (`tests/`) que necesitan verificar la implementación interna. Movido desde el antiguo paquete de nivel superior `backend/` en el Sprint 2.6.2 (ver [ADR-006](../architecture/adr/ADR-006-internal-namespace-refactor.md)). |

```python
# Correcto — cualquier consumidor externo:
from teaf import Application, Module, ModuleBuilder
from teaf.security import JWTProvider, SecurityMiddleware, authorize   # también válido: from teaf import ...
from teaf.api import ApiGateway, RateLimiter, RateLimitRule            # también válido: from teaf import ...

# Incorrecto — nunca fuera de este repositorio, ni en examples/:
from teaf._internal.core.application import create_app
from teaf._internal.sdk.module_base import ModuleBase
from teaf._internal.security.tokens.jwt_provider import JWTTokenProvider
from teaf._internal.api.ratelimit.limiter import RateLimiter
```

No hay una lista de excepciones: si un símbolo de `teaf/_internal/` es genuinamente útil para un consumidor externo, la corrección es exponerlo desde la fachada correspondiente de `teaf/` (ver [PACKAGE-STRUCTURE.md](PACKAGE-STRUCTURE.md)) — nunca "solo por esta vez" importar `teaf._internal.*` directamente desde fuera.

## 2. Por qué

`teaf/_internal/` es libre de reorganizarse entre Sprints — mover un archivo, renombrar una clase interna, dividir un módulo — sin que eso rompa a ningún consumidor de `teaf`, siempre que el contrato de `teaf/__init__.py` no cambie (ver `PUBLIC_API_VERSION` en [VERSIONING.md](VERSIONING.md)). Si un consumidor externo importara `teaf._internal.sdk.module_base.ModuleBase` directamente, cualquier reorganización interna de `teaf/_internal/sdk/` sería, de hecho, un cambio incompatible para ese consumidor — exactamente lo que la fachada existe para evitar.

## 3. El verificador de límites

`scripts/check_public_api_boundary.py` analiza estáticamente (vía `ast`, sin ejecutar ningún código) un árbol de archivos `.py` y reporta cualquier `import teaf._internal...`/`from teaf._internal... import ...` encontrado:

```bash
python scripts/check_public_api_boundary.py examples/
# OK — ningún import de namespace privado ('teaf._internal',) encontrado.
```

Se ejecuta hoy sobre `examples/` (ver `tests/unit/test_import_boundary_checker.py`, que lo invoca como parte de la suite de pruebas) — sienta la base para una futura verificación en CI sobre cualquier proyecto externo o plantilla de arranque, sin estar cableado a ningún pipeline todavía (ver Sprint 2.5.1, sección 8).

`teaf/` mismo, y `tests/`, quedan fuera del alcance de este verificador a propósito: ambos necesitan importar `teaf._internal.*` para funcionar (son la implementación y sus pruebas de caja blanca, respectivamente) — el límite aplica a *consumidores*, no a este repositorio en su totalidad.

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
