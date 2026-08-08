# Dependencias — política, matriz y auditoría

Qué depende TEAF de terceros, por qué esa versión, y cómo se comprueba que no arrastra
vulnerabilidades conocidas. La justificación de **qué tecnología** se elige está en
[STACK.md](architecture/STACK.md); aquí está la de **qué versión** y su estado de seguridad. Para
qué depende TEAF del **sistema operativo** —y las dos únicas cifras cuya implementación difiere
entre POSIX y Windows— ver [PLATFORM-COMPATIBILITY.md](PLATFORM-COMPATIBILITY.md).

## Política

- **Versiones fijadas con `==`**, nunca rangos abiertos. Una compilación reproducible es un
  requisito de seguridad, no una preferencia de estilo.
- `requirements.txt` y `pyproject.toml` **siempre sincronizados** — lo verifica la revisión de
  dependencias de [SECURITY-REVIEW.md](SECURITY-REVIEW.md).
- **Ninguna dependencia nueva sin ADR** ([CLAUDE.md](../CLAUDE.md) §4), y ninguna que resuelva algo
  que Python, Starlette, FastAPI o el propio TEAF ya resuelven.
- Las dependencias **opcionales** viven en `[project.optional-dependencies]` y se importan de forma
  perezosa: no instalarlas nunca puede romper el arranque.

## Auditoría de vulnerabilidades

```bash
python scripts/check_dependency_audit.py     # o la puerta `dependencies`
```

Ejecuta `pip-audit` sobre `requirements.txt` y **falla ante cualquier aviso** que no esté
explícitamente aceptado en
[`docs/security/accepted-vulnerabilities.json`](security/accepted-vulnerabilities.json), con
identificador, severidad, versión afectada, versión objetivo y justificación.

**Estado en v0.10.0-alpha: 0 vulnerabilidades, 0 excepciones aceptadas.**

## Modernización de Sprint 3.0 — matriz de compatibilidad

Sprint 2.9.2 aceptó 7 vulnerabilidades de Starlette porque `fastapi==0.115.6` fijaba
`starlette<0.42.0` y ninguna corrección era alcanzable. Sprint 3.0 desbloquea esa deuda.

| Componente | Actual (v0.9.2) | Objetivo (v0.10.0) | Motivo | Compatibilidad | Impacto de seguridad |
|---|---|---|---|---|---|
| **fastapi** | 0.115.6 | **0.141.1** | Su pin `starlette<0.42.0` bloqueaba las 7 correcciones. 0.141.1 pide `starlette>=0.46.0` **sin techo**. | 1 prueba adaptada (ver abajo). `requires_python>=3.10`, usamos 3.11. | Indirecto: es lo que habilita el salto de Starlette. |
| **starlette** | 0.41.3 | **1.4.1** | Corrige las 7 vulnerabilidades aceptadas. | TEAF **no usa ninguna API eliminada en 1.0** — ya usaba `lifespan=` y `add_exception_handler`. | **Resuelve 7 avisos**: PYSEC-2026-161, -248, -249, -1941, -1942, -2280, -2281. |
| **pydantic** | 2.10.4 | 2.10.4 (sin cambio) | fastapi 0.141.1 pide `>=2.9.0`; el actual cumple. | Sin cambios. | Sin avisos. |
| **httpx** | 0.28.1 | 0.28.1 (sin cambio) | En starlette es solo `extra == "full"`, con `httpx<0.29.0`. **No fuerza httpx 2.** | Sin cambios. | Sin avisos. |
| **anyio** | 4.14.2 | 4.14.2 (sin cambio) | starlette 1.4.1 pide `anyio<5,>=3.6.2`. | Sin cambios. | Sin avisos. |
| **pyjwt** | 2.13.0 | 2.13.0 (sin cambio) | Ya se actualizó en Sprint 2.9.2 al corregir 6 avisos. | Sin cambios. | Sin avisos. |

### Lo que rompió, y lo que no

La migración fue **una prueba y dos constantes**, sobre 1.170 pruebas:

1. **`app.routes` ya no aplana los routers incluidos.** Desde FastAPI 0.141, `include_router`
   envuelve cada router en un `_IncludedRouter`, así que recorrer `app.routes` ya no ve sus rutas.
   No es un fallo de comportamiento —todos los endpoints responden y el esquema OpenAPI publica las
   15 rutas— sino de **introspección**. `test_create_app_registers_system_routes` pasa a
   comprobarlo sobre `app.openapi()["paths"]`, que además es mejor prueba: verifica que la ruta
   existe *y* que se publica. TEAF nunca recorría `app.routes` en su propio código.
2. **`HTTP_422_UNPROCESSABLE_ENTITY` está deprecada** a favor de `HTTP_422_UNPROCESSABLE_CONTENT`
   (mismo valor, 422). Tres usos en `middleware/exception_handler.py`, actualizados. Ninguna
   respuesta cambia.

Nada más: ni los 12 middlewares sobre `BaseHTTPMiddleware`, ni `TestClient`, ni el `lifespan`, ni
`MutableHeaders`/`starlette.types` necesitaron un solo cambio. `mypy --strict` sigue en **0 errores
sobre 226 ficheros**.

### Aviso conocido y no accionable

`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2
instead`. Lo emite el `TestClient` de FastAPI, no código de TEAF. Migrar a `httpx2` es un salto de
versión mayor de una dependencia que TEAF también usa directamente (proveedores OIDC/Azure AD), y
queda como backlog para un Sprint posterior. No hay vulnerabilidad asociada.

## Dependencias de runtime

18 paquetes fijados en [`requirements.txt`](../requirements.txt). Todas con licencia MIT, BSD o
Apache-2.0 — compatibles con uso empresarial.

Cuatro no se importan directamente y **es deliberado**: `pydantic` (transitiva de FastAPI y
pydantic-settings, fijada a propósito para que una actualización de FastAPI no arrastre una versión
no probada), `uvicorn` (servidor: se invoca, no se importa) y `aiosqlite`/`asyncpg` (drivers que
SQLAlchemy carga desde la cadena de conexión). No son sobrantes; no las elimine.

## Dependencias opcionales

| Extra | Paquete | Para qué | Si no está instalado |
|---|---|---|---|
| `redis` | `redis>=5.0` | Almacenes distribuidos de rate limiting, cuotas e idempotencia, y el proveedor de caché ([ADR-012](architecture/adr/ADR-012-redis-optional-infrastructure.md)) | El módulo de caché no se construye y TEAF funciona con los almacenes en memoria. El import es perezoso. |

```bash
pip install teaf[redis]
```
