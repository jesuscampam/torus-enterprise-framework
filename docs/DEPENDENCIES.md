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

## Sprint 3.0.3 — compatibilidad con Python 3.14

Hasta v0.10.2-alpha, `pip install -e .` **fallaba en Python 3.14**. El código de TEAF no tenía
nada que ver: el fallo era de tres dependencias fijadas a versiones anteriores a 3.14. Las
versiones de Python que TEAF declara soportar y su estado de verificación están en
[PLATFORM-COMPATIBILITY.md](PLATFORM-COMPATIBILITY.md#versiones-de-python).

### Por qué falla, y por qué el rueda (*wheel*) es lo que decide

Al instalar, pip elige un artefacto según su *tag*. Cuál toque determina si la instalación es
instantánea o si intenta compilar:

| Tag | Qué es | En 3.14 |
|---|---|---|
| `cp314-…` | Binario compilado específicamente para CPython 3.14 | Se instala tal cual |
| `abi3` | Binario contra la ABI estable de CPython, válido en cualquier 3.x ≥ su tag | Se instala tal cual |
| `py3-none-any` | Python puro, sin extensión nativa | Se instala, pero **sin la aceleración en C** |
| *(ninguno)* | Solo hay *sdist* | **Se compila en la máquina** — necesita toolchain, y puede fallar |

El último caso es el que rompía: sin wheel, pip cae al *sdist* y compila. `pydantic-core` se
compila con Rust vía PyO3, y **PyO3 0.22.6 no admite Python 3.14** — no es falta de toolchain, es
un techo del propio compilador. Por eso `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` "funciona": desactiva
esa comprobación de versión y construye contra una ABI que no se ha validado para 3.14. Es un
`--force`, no una solución, y este sprint lo descarta expresamente.

### Auditoría: 17 paquetes con extensión nativa

Revisados todos los paquetes con código nativo del árbol de dependencias, en su versión fijada:

| Paquete | Pin en v0.10.2 | Estado en 3.14 | Cómo se resuelve |
|---|---|---|---|
| **pydantic-core** | 2.27.2 (vía `pydantic==2.10.4`) | ❌ **Bloquea** | Sin wheel `cp314`; compilar falla en PyO3 |
| **asyncpg** | 0.30.0 | ❌ **Bloquea** | Sin wheel `cp314`; compila con C solo si hay toolchain (86 s medidos) |
| **sqlalchemy** | 2.0.36 | ❌ **Bloquea** | Instala por fallback puro, pero **falla al importar** (ver abajo) |
| mypy, black | 1.14.1, 24.10.0 | ⚠️ Degradado | Fallback `py3-none-any`, sin aceleración |
| cryptography, bcrypt, protobuf | — | ✅ | `abi3` |
| argon2-cffi-bindings, cffi, greenlet, httptools, uvloop, watchfiles, websockets, markupsafe, coverage | — | ✅ | `cp314` nativo |

### Los tres pins que cambian — y solo tres

| Paquete | Antes | Después | Por qué exactamente esa versión |
|---|---|---|---|
| `pydantic` | 2.10.4 | **2.12.0** | Primera versión que fija `pydantic-core==2.41.1`, con wheels `cp314`. `pydantic-core` publica `cp314` desde 2.35.0, pero **ninguna** `pydantic` lo fija hasta 2.12.0 — no hay salto menor posible |
| `asyncpg` | 0.30.0 | **0.31.0** | Primera (y a fecha de hoy única) versión con wheel `cp314` |
| `sqlalchemy[asyncio]` | 2.0.36 | **2.0.45** | 2.0.36 instala pero **revienta en el import**: `TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'` (`sqlalchemy/util/typing.py:478`). Bisecado: 2.0.37 ya importa; 2.0.45 además publica wheels `cp314` con las extensiones en C |

Nada más se toca. En particular **no se actualizan FastAPI ni Starlette**: el sprint lo prohíbe
salvo incompatibilidad demostrable, y no la hay — `fastapi==0.141.1` pide `pydantic>=2.9.0`, que
2.12.0 satisface. `mypy` y `black` se quedan: instalan por fallback puro y subirlos sería una
actualización sin bloqueo que la justifique. `pydantic-settings==2.7.0` tampoco cambia: su
constraint `pydantic>=2.7.0` la cumple 2.12.0, y las pruebas no revelaron ningún uso de internals
alterados.

### Corrección de una clasificación previa

La auditoría inicial de este sprint clasificó `sqlalchemy 2.0.36` como *"instala, solo pierde la
aceleración en C"* — leyendo los tags de los artefactos publicados. **Era incorrecto.** El paquete
sí instala, pero falla al importar en 3.14. Solo se descubrió al ejecutar de verdad sobre un
CPython 3.14, no analizando metadata: un wheel `py3-none-any` garantiza que pip encuentre algo que
instalar, no que ese código funcione en el intérprete de destino.

### Qué se verificó y qué no

- **Verificado**: instalación y las **1.272 pruebas en verde** sobre tres intérpretes reales —
  CPython **3.11.15**, **3.13.12** y **3.14.0rc2** (este último descargado con `uv`), con resultados
  idénticos en los tres. `pydantic` 2.10 → 2.12 (dos versiones menores) **no produjo ningún cambio
  de comportamiento observable** en la API pública.
- **No verificado**: `asyncpg 0.31.0` contra un PostgreSQL real. TEAF nunca lo importa —SQLAlchemy
  lo carga desde la cadena de conexión— y la suite usa `aiosqlite`. El cambio de pin es seguro para
  la instalación; el comportamiento del driver contra un servidor no se ha ejercitado aquí.
- **No verificado**: 3.14.**6** (la versión del usuario). Lo probado es 3.14.0rc2. Comparten el ABI
  `cp314`, que es lo que decide la selección de wheels, pero no es la misma compilación.
- **Pendiente, deliberado**: no se creó CI con matriz de versiones. Sería infraestructura nueva, que
  este sprint deja fuera de alcance; queda en [BACKLOG.md](roadmap/BACKLOG.md).

### Efecto colateral de `pydantic` 2.12 sobre la superficie pública

`teaf.Configuration` es un `BaseModel` de pydantic, así que hereda sus métodos — y el fichero de
referencia de la puerta `public-api` (`docs/public-api/api-surface.json`) captura sus firmas.
Actualizar pydantic movió cuatro de ellas:

| Método | Cambio | ¿Rompe? |
|---|---|---|
| `model_dump` | `by_alias: bool = False` → `bool \| None = None` | **No** — `None` significa "usa `serialize_by_alias` del modelo", que en `Settings` no está puesto y resuelve a `False` |
| `model_dump_json` | Igual | **No**, por lo mismo |
| `model_post_init` | `_BaseModel__context` → `context`, posicional-solo | **No** — el nombre anterior estaba *name-mangled*; nadie podía pasarlo por palabra clave de forma razonable |
| *(varios)* | Parámetros nuevos: `fallback`, `exclude_computed_fields`, `by_name`, `ensure_ascii`, `union_format` | **No** — todos opcionales; ampliar no rompe |

Se comprobó **midiendo, no razonando**: se levantó un entorno con `pydantic==2.10.4` y se volcó la
configuración completa en ambas versiones. Las **484 líneas de salida son idénticas**. Por eso
`PUBLIC_API_VERSION` se queda en `2.0.0` y solo se regeneró el fichero de referencia (1 símbolo
afectado de 199; ninguno añadido ni eliminado). La equivalencia queda fijada por una prueba en
`tests/unit/test_config.py`. **La decisión queda sujeta a revisión de un CODEOWNER**
([CLAUDE.md](../CLAUDE.md) §8): quien revise puede sostener que un cambio de firma merece MAJOR
aunque no altere el comportamiento.

### Deuda detectada, fuera de alcance

`starlette` **no está fijado** en `requirements.txt`: entra como transitiva de FastAPI, cuyo
constraint (`>=0.46.0`) no tiene techo. Consecuencia observada: una instalación limpia en 3.14 trajo
`starlette 1.6.0`, mientras este contenedor tiene `1.4.1`. Es anterior a este sprint y contradice la
política de "versiones fijadas con `==`" de este mismo documento. No se corrige aquí porque fijarlo
es una decisión de dependencias por derecho propio, no un efecto colateral de dar soporte a 3.14.

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
