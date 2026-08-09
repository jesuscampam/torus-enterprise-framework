# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### TEAF 3.0 Final Hardening

Cierra las dos inconsistencias que el propio *release gate* de la línea 3.0 destapaba. **No es un
Sprint 3.0.4** —no existe tal cosa documentada— sino el cierre de la línea 3.0 antes de abrir 3.1.
Sin funcionalidad nueva, sin dependencias nuevas, sin tocar Runtime, Database, Redis, Security,
API Gateway ni observabilidad.

#### Added

- **`teaf.__version__`.** `import teaf; teaf.__version__` devuelve `"0.10.3-alpha"`. Hasta ahora la
  versión solo se alcanzaba por `teaf.Version.framework` o `teaf.version.FRAMEWORK_VERSION` —ambas
  correctas, ninguna convencional—, así que cualquier herramienta genérica (un `--version` de una
  app consumidora, un script de release) tenía que conocer la estructura interna de TEAF para algo
  trivial.
  - Es un **alias, no una fuente**: deriva de `FRAMEWORK_VERSION`, que nace en
    `teaf/_internal/core/application.py`. El literal no se repite en ningún sitio.
  - **No entra en `__all__`**: `__all__` enumera símbolos importables, no metadatos del módulo, y
    Python ya excluye los dunder de `from teaf import *`. La superficie pública sigue siendo de 199
    símbolos y `PUBLIC_API_VERSION` **no cambia** (sigue `2.0.0`): es una adición, no una ruptura.
  - 4 pruebas nuevas en `tests/unit/test_teaf_version.py`: existencia, identidad con la fuente
    canónica, coherencia con la metadata instalada (normalizando PEP 440) y ausencia de `__all__`.
- **`RuntimeWarning` es error en pytest**, declarado en `pyproject.toml` para que forme parte del
  contrato reproducible y no dependa de recordar `-W error::RuntimeWarning`.

#### Fixed

- **La política anterior no habría detectado el fallo que la motiva.** La primera versión de este
  cambio declaraba solo `error::RuntimeWarning`. Al comprobarlo con una **regresión simulada** —un
  test que llama a una corrutina sin `await`— resultó que **seguía pasando en verde**: ese aviso no
  llega como un `RuntimeWarning` corriente, lo emite el recolector de basura al destruir la
  corrutina, viaja por el gancho *unraisable* y pytest lo envuelve en
  `PytestUnraisableExceptionWarning`. Añadido `error::pytest.PytestUnraisableExceptionWarning`, la
  misma regresión **falla como debe**. La cadena completa, ya verificada extremo a extremo:

    ```
    await olvidado → GC destruye la corrutina → RuntimeWarning
      → gancho unraisable → PytestUnraisableExceptionWarning → error → FAIL
    ```

  - **No se silencia ningún `RuntimeWarning`**, ni globalmente ni por archivo: activar la política
    no obligó a exceptuar nada, la suite entera siguió en verde.
  - 4 pruebas nuevas en `tests/unit/test_runtime_warning_policy.py`, incluida una específica para el
    filtro *unraisable* —el contraintuitivo— para que nadie lo retire por parecer redundante. La
    comprobación con una corrutina real **no** entra en la suite: depende de cuándo actúe el
    recolector, y sería justo el comportamiento frágil que hay que evitar.

- **Un error de lint latente en código ya commiteado**, encontrado de paso: `UP038` sobre
  `isinstance(value, (list, tuple))` en `teaf/_internal/api/module/configuration.py`. No lo
  introduce este cambio —se confirmó con `git stash`: la puerta falla igual sin él— y llevaba
  enmascarado por la caché de ruff, que se invalidó al pasar `black`. Corregido a
  `isinstance(value, list | tuple)`: comportamiento idéntico, una línea.

#### Verificado

**1289 pruebas en verde, 0 fallos, 11 skips** (los mismos de siempre: Redis no accesible,
infraestructura externa). 25/25 ejemplos, boundary de API pública en verde, Reference App sin
modificar y **11 de 12 puertas de calidad**.

La puerta número 12, `benchmarks`, **queda en rojo por la oscilación del anfitrión ya documentada**
en [BENCHMARKS.md](docs/BENCHMARKS.md), no por este cambio: son las mismas siete mediciones a
+62 %/+77 %, y GZip mide 2033 µs frente a los 2048 µs medidos en sesiones anteriores con dos juegos
de dependencias distintos. Este trabajo añade un alias de módulo y dos filtros de pytest — nada que
pueda tocar la resolución del contenedor de DI, el EventBus ni zlib. **La baseline no se ha
regenerado**, por el mismo motivo que las veces anteriores.

## [0.10.3-alpha] - 2026-08-08

Compatibilidad con Python 3.14. Hasta esta versión, `pip install -e .` **fallaba en Python 3.14**.
El código de TEAF no tenía nada que ver: el bloqueo estaba íntegramente en tres dependencias
fijadas a versiones anteriores a 3.14. Sin cambios en la API pública (`PUBLIC_API_VERSION` sigue en
`2.0.0`), sin dependencias nuevas y **sin perder soporte para 3.11, 3.12 ni 3.13**.

### Fixed

- **TEAF ya se instala y funciona en Python 3.14.** Tres pins actualizados, y solo tres — cada uno
  con un bloqueo demostrado detrás, ninguno "por estar al día":
  - `pydantic` **2.10.4 → 2.12.0**. Su `pydantic-core==2.27.2` no publica wheel `cp314`, así que pip
    caía al *sdist* y compilaba con Rust; **PyO3 0.22.6 no admite Python 3.14** y la compilación
    aborta. No es falta de toolchain: es un techo del propio compilador, y por eso instalar Rust a
    mano no lo resuelve. 2.12.0 es la primera `pydantic` que fija `pydantic-core==2.41.1`, con
    wheels `cp314`; `pydantic-core` los publica desde 2.35.0, pero ninguna `pydantic` lo fija antes,
    de modo que no había salto menor posible.
  - `asyncpg` **0.30.0 → 0.31.0**. Tampoco publicaba wheel `cp314`. Compila con C —86 s medidos
    aquí— pero falla en cualquier máquina sin toolchain. 0.31.0 es la primera versión con wheel.
    **Este bloqueante no estaba en el informe original**; lo encontró la auditoría.
  - `sqlalchemy[asyncio]` **2.0.36 → 2.0.45**. Instala en 3.14 por el fallback `py3-none-any`, pero
    **revienta al importar**: `TypeError: descriptor '__getitem__' requires a 'typing.Union' object
    but received a 'tuple'` (`sqlalchemy/util/typing.py:478`). Bisecado: 2.0.37 ya importa; 2.0.45
    además trae wheels `cp314` con las extensiones en C. Este fallo **contradice la clasificación
    de la auditoría inicial de este mismo sprint**, que lo dio por "instala, solo pierde
    aceleración" leyendo los tags publicados — se descubrió al ejecutar de verdad sobre un CPython
    3.14, no analizando metadata.

  `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` **no se usa**: desactiva la comprobación de versión de
  PyO3 y construye contra una ABI no validada para 3.14. Es un `--force`, no una corrección.

- **`starlette` y `greenlet` pasan a estar fijadas** (`==1.4.1` y `==3.5.4`). Ninguna aparecía en los
  manifiestos: entraban como transitivas de `fastapi` y de `sqlalchemy[asyncio]`, cuyos constraints
  no tienen techo (`starlette>=0.46.0`, `greenlet>=1`). El efecto era medible — el mismo commit
  instalaba **starlette 1.4.1** en el entorno de desarrollo y **1.6.0** en una instalación limpia en
  3.14, es decir, distinta cadena HTTP con el mismo código.
  - `starlette 1.4.1` es la versión contra la que se validó `fastapi 0.141.1` en el Sprint 3.0 y la
    que corrigió sus 7 CVE; fijarla no introduce nada nuevo, congela lo ya probado. Tiene un efecto
    añadido: los middlewares de TEAF heredan de `BaseHTTPMiddleware`, así que la versión de starlette
    entra en el snapshot de API pública — fijarla evita que `api-surface.json` se mueva solo.
  - `greenlet 3.5.4` se fija sobre todo por ser **código nativo**: un greenlet futuro sin wheel para
    el Python de turno reproduce exactamente el fallo que originó este sprint.

### Changed

- **Clasificadores `Programming Language :: Python :: 3.12`, `:: 3.13` y `:: 3.14`** en
  `pyproject.toml`. `requires-python` **se queda en `>=3.11`**: ganar 3.14 no cuesta las versiones
  anteriores, y subir el suelo habría roto a los consumidores de 3.11/3.12.

### Added

- **5 pruebas nuevas** en `tests/unit/test_python_version_support.py` y 3 en
  `test_packaging_metadata.py`, que fijan que **la metadata no mienta**: que `requires-python` y los
  clasificadores coincidan, que el rango declarado no tenga huecos, que 3.13 no se pierda al ganar
  3.14, y que el intérprete que ejecuta la suite caiga dentro de lo declarado.
- **La política de pins deja de ser solo prosa.** `docs/DEPENDENCIES.md` decía desde siempre
  "versiones fijadas con `==`, nunca rangos abiertos", y nada lo comprobaba — de ahí que dos
  transitivas llevaran flotando sin que saltara nada. Ahora una prueba falla si alguna línea de
  `requirements.txt` abandona el `==`, y otra fija que `starlette` y `greenlet` sigan declaradas.
- **Auditoría del cierre transitivo completo**: 58 paquetes de runtime, de los que **7 llevan código
  nativo sin fijar** — la clase de fallo exacta de este sprint. `pydantic-core` está controlada de
  facto (`pydantic` la fija exacto) y `greenlet` se fija aquí; las otras 5 (`cryptography`, `cffi`,
  `argon2-cffi-bindings`, `markupsafe`, `protobuf`) **se dejan a propósito**: ninguna bloquea hoy y
  elegirles versión sin un bloqueo que lo justifique sería la actualización a ciegas que el sprint
  prohíbe. Cerrarlo bien exige un lockfile, que es decisión de arquitectura con ADR.
- **Matriz de wheels para macOS ARM64 + CPython 3.14** en `docs/DEPENDENCIES.md`. No hay Mac en el
  entorno, así que no se ejecutó nada allí — pero sí se verificó, consultando PyPI, **qué wheel
  elegiría pip en esa plataforma exacta**, que es el mecanismo que falló. Ninguno de los 20 paquetes
  cae al *sdist*: ninguno compila, ni con Rust ni con C.
- [PLATFORM-COMPATIBILITY.md](docs/PLATFORM-COMPATIBILITY.md) gana la sección **Versiones de
  Python**, con la misma distinción VERIFICADO / COMPATIBLE POR DISEÑO que ya aplicaba a los
  sistemas operativos.
- [DEPENDENCIES.md](docs/DEPENDENCIES.md) gana la auditoría completa de los **17 paquetes con
  extensión nativa**, la tabla de qué significa cada *tag* de wheel, y la corrección explícita de
  la clasificación errónea de `sqlalchemy`.

### Dos hallazgos que la validación destapó — ninguno bloquea, ambos exigen revisión humana

1. **La puerta `public-api` detectó 4 cambios de firma en `teaf.Configuration`**, todos heredados de
   `pydantic.main.BaseModel` — ninguno es código de TEAF: `model_dump` y `model_dump_json` cambian
   el defecto de `by_alias` (`False` → `None`), y `model_post_init` renombra su parámetro
   (`_BaseModel__context` → `context`, ahora posicional-solo). El sprint obliga a **detenerse ante
   cambios de comportamiento observables**, así que se midió en vez de suponer: se levantó un
   entorno con `pydantic==2.10.4` y se volcó la configuración completa en ambas versiones. Las **484
   líneas de salida son idénticas** — `by_alias=None` significa "usa `serialize_by_alias` del
   modelo", que en `Settings` no está puesto y resuelve a `False`. Es decir: **la firma cambia, el
   comportamiento no**.
   - Por eso **`PUBLIC_API_VERSION` se queda en `2.0.0`** y se regeneró el fichero de referencia
     `docs/public-api/api-surface.json` (1 símbolo afectado de 199, ninguno añadido ni eliminado).
   - La equivalencia queda fijada por una prueba nueva en `tests/unit/test_config.py`, para que
     activar `serialize_by_alias` en el futuro —que sí rompería
     `from_mapping(settings.model_dump())`— falle de forma visible.
   - **Decisión sujeta a revisión de un CODEOWNER** ([CLAUDE.md](CLAUDE.md) §8): quien revise puede
     concluir que un cambio de firma, aun sin efecto observable, merece MAJOR igualmente.

2. **La puerta `benchmarks` falló a mitad del sprint, y no por este cambio.** Seis mediciones salían
   +64 % a +80 % sobre la baseline. Se descartó la hipótesis obvia con un experimento controlado:
   los mismos benchmarks, en la misma máquina y en el mismo momento, **con el pin anterior
   `pydantic==2.10.4`**, daban la misma regresión (GZip: 2048.70 µs con 2.10.4 frente a 2048.12 µs
   con 2.12.0 — el mismo número). Además, lo degradado incluía compresión GZip y resolución del
   contenedor de DI, que no tocan `pydantic` ni por asomo. Era el anfitrión.
   - **La baseline no se regeneró**, y el episodio acabó dándole la razón a esa decisión: en la
     validación final la puerta **volvió sola a verde** sin tocar un solo número de `baseline.json`.
     De haberla reescrito para "arreglar" el rojo, hoy estaría inflada un 70 % de forma permanente.
     Contado en [BENCHMARKS.md](docs/BENCHMARKS.md) como caso práctico.

### Verificado / no verificado

- **Verificado**: en **cuatro** intérpretes reales — CPython **3.11.15**, **3.12.3**, **3.13.12** y
  **3.14.0rc2** (vía `uv`) — cada uno en un **venv recreado desde cero**, con `pip install -e .` y
  **1.281 pruebas en verde**, resultados idénticos en los cuatro. En 3.14 se ejercitaron además
  `from teaf import Application`, `Version.as_dict()`, el ciclo `bootstrapping → running → stopped`
  del `Runtime` y los cuatro endpoints de sistema, con `memoryRssBytes` y `cpuTimeSeconds` reales.
  La subida de `pydantic` de 2.10 a 2.12 —dos versiones menores— **no produjo ningún cambio de
  comportamiento observable** en la API pública.
  - *(Corrección a la primera versión de esta entrada, que daba 3.12 por no verificado "sin
    intérprete disponible": sí lo hay, `/usr/bin/python3.12`. Ahora está verificado de verdad.)*
- **No verificado**: `asyncpg 0.31.0` contra un PostgreSQL real; Python 3.14.**6** (lo probado es
  3.14.0rc2, mismo ABI `cp314` pero distinta compilación); y la combinación *Windows o macOS × 3.14*,
  que hereda las reservas ya declaradas para esas plataformas. De macOS ARM64 sí se verificó la
  **disponibilidad de wheels**, que es el mecanismo que falló, no la ejecución.
- **Pendiente, deliberado**: no se creó CI con matriz de versiones — es infraestructura nueva, fuera
  del alcance del sprint. Anotado en [BACKLOG.md](docs/roadmap/BACKLOG.md), junto con el lockfile
  que haría falta para fijar las 5 transitivas nativas restantes.

### Qué no cambió

- **Ni una línea del código del framework.** Se auditó el árbol en busca de APIs retiradas en
  3.13/3.14 (`datetime.utcnow`, `distutils`, `asyncio.get_event_loop`, `imp`,
  `pkgutil.find_loader`): ninguna aparece.
- **FastAPI 0.141.1 y Starlette** no se actualizan: no hay incompatibilidad demostrable —
  `fastapi` pide `pydantic>=2.9.0`, que 2.12.0 cumple.
- `mypy`, `black` y `pydantic-settings` se quedan como estaban: instalan en 3.14 y no hay bloqueo
  que justifique subirlos.
- **`teaf-reference-app`**: no se ha modificado.

## [0.10.2-alpha] - 2026-08-08

Cross-Platform Runtime Compatibility. Completa el trabajo multiplataforma que empezó
[0.10.1-alpha](#0101-alpha---2026-08-08) cerrando el lado macOS. Sin dependencias externas nuevas,
sin cambios en la API pública (`PUBLIC_API_VERSION` sigue en `2.0.0`).

### Fixed

- **La memoria reportada en macOS era 1024 veces la real.** `_posix_memory_rss_bytes` multiplicaba
  `ru_maxrss` por 1024 sin mirar la plataforma, pero **`ru_maxrss` no usa la misma unidad en todos
  los POSIX**: en Linux y FreeBSD viene en KiB, y en macOS/Darwin **ya viene en bytes**
  (`getrusage(2)` de cada sistema lo documenta explícitamente). El defecto era silencioso — no
  fallaba, solo devolvía un número equivocado en `GET /runtime/info`.
  - Corregido con `_RU_MAXRSS_TO_BYTES`, un factor resuelto una sola vez al importar (`1` en
    `darwin`, `1024` en el resto). Es el mismo reparto que hace **mypy** en `dmypy_server.py`,
    corroboración independiente de cuál es el lado correcto.
  - **Linux no se ve afectado**: mismo valor, mismo código, misma ruta de ejecución.
  - Es la única desviación deliberada de "no cambiar el comportamiento existente de Linux/macOS"
    de este sprint, y se hace porque el valor anterior era incorrecto, no una convención distinta:
    `memory_rss_bytes` promete bytes y en macOS no los devolvía. Declarado en
    [PLATFORM-COMPATIBILITY.md](docs/PLATFORM-COMPATIBILITY.md).

### Added

- **5 pruebas nuevas** (15 en total en `test_process_metrics_platform.py`): el factor de unidades
  para `linux`/`freebsd`/`darwin` simulados, un contraste en Linux contra `VmHWM` de
  `/proc/self/status` —el mismo pico de RSS en una unidad sin ambigüedad—, y una prueba de que
  macOS despacha al backend POSIX y **nunca** toca `ctypes.windll`.
- [PLATFORM-COMPATIBILITY.md](docs/PLATFORM-COMPATIBILITY.md) gana la matriz de métricas por
  plataforma (Linux · macOS · Windows) y una sección de **limitaciones** que documenta que las
  cifras **no son perfectamente equivalentes** entre sistemas: `ru_maxrss` es un *pico histórico*
  mientras `WorkingSetSize` es un *valor actual*; Working Set no es exactamente RSS; y
  `GetProcessTimes` tiene ~15,6 ms de granularidad frente a los microsegundos de `getrusage`.
- Nota explícita de que el camino Windows **no filtra recursos**: `GetCurrentProcess()` devuelve un
  *pseudo-handle*, no un handle real, así que no hay nada que cerrar.

## [0.10.1-alpha] - 2026-08-08

Windows Compatibility Patch. Corrige un defecto que impedía `from teaf import Application` en
Windows. Sin funcionalidad nueva, sin cambios de comportamiento en Linux/Unix, sin ruptura de API
pública.

### Fixed

- **`ModuleNotFoundError: No module named 'resource'` en Windows.** `teaf/_internal/runtime/runtime.py`
  importaba `resource` —módulo estándar exclusivo de POSIX, sin equivalente en Windows— a nivel de
  módulo. Como `Runtime` está en la cadena de import de `from teaf import Application` (vía
  `teaf.api` → `ApiProtectionModule` → `ModuleContext` → `Runtime`), cualquier intento de importar
  TEAF en Windows fallaba antes de que la aplicación que lo consume ejecutara una sola línea propia.
  Reportado al integrar `teaf-reference-app` en Windows.

### Added

- **`teaf._internal.runtime.process_metrics`** — abstracción de plataforma para las dos únicas
  cifras que usaban `resource`: memoria residente y tiempo de CPU, expuestas por
  `Runtime.diagnostics()` vía `GET /runtime/info`. Diagnóstico auxiliar, no comportamiento
  funcional — ya eran `int | None`/`float | None` desde Sprint 2.8. El camino POSIX
  (`resource.getrusage`) no cambia una sola línea; Windows obtiene su propia implementación real
  —`os.times()` para CPU (documentada como portátil por la librería estándar), `ctypes` +
  `GetProcessMemoryInfo` (`psapi.dll`) para memoria—, sin dependencia nueva.
- [`docs/PLATFORM-COMPATIBILITY.md`](docs/PLATFORM-COMPATIBILITY.md) — causa raíz, la abstracción,
  auditoría completa de otras APIs exclusivas de plataforma (ninguna encontrada), y el estado real
  de verificación por plataforma: **Linux verificado**; **Windows y macOS compatibles por diseño,
  no verificados en una máquina real** — no se declara soporte sin haberlo comprobado.
- `tests/unit/test_process_metrics_platform.py` (10 pruebas) y
  `tests/integration/test_windows_compatibility.py` (4 pruebas): regresión del import guardado por
  plataforma (AST), el camino POSIX byte a byte, y una simulación estructural de la superficie de
  Windows (`ctypes.windll` sustituido por un doble) — documentada explícitamente como verificación
  de mecánica, no como validación en un Windows real.

### Auditoría

Búsqueda completa en el repositorio de otras dependencias exclusivas de plataforma (`fcntl`, `pwd`,
`grp`, `termios`, `tty`, `pty`, `signal` específico de POSIX, `os.uname`, `os.fork`, `os.getuid`,
`os.getgid`, rutas `/etc/`): **ninguna**, ni dentro de `teaf/` ni en el resto del repositorio.
`loadtests/harness.py` también usa `resource`, pero es herramienta de desarrollo fuera del paquete
distribuido y no bloquea `from teaf import Application` — queda documentado, no corregido, por su
propia regla de alcance.

## [0.10.0-alpha] - 2026-08-07

Sprint 3.0 — **Infraestructura de producción y modernización del runtime**. Cierra los cuatro pendientes que la línea 2.9 dejó explícitamente aplazados. Sin funcionalidad de negocio nueva: el sprint no hace TEAF más grande, sino más seguro, portable y auditable.

**Ruptura de API pública**: `PUBLIC_API_VERSION` sube de `1.0.0` a `2.0.0`. Un único cambio incompatible, sin consumidores reales posibles — ver *Changed*. Superficie: 192 → **199 símbolos**, 0 eliminados, 0 renombrados.

### Added

- **Módulo de caché distribuida** ([ADR-012](docs/architecture/adr/ADR-012-redis-optional-infrastructure.md)) — quinto módulo construido sobre el [Module SDK](docs/sdk/SDK.md), calcado del patrón de `DatabaseModule`. Desbloquea el escalado horizontal: los almacenes en memoria son por proceso, así que con 4 réplicas un límite de 100 req/min son 400 en la práctica, una cuota diaria se cuadruplica y **un reintento idempotente que caiga en otra réplica se ejecuta dos veces**.
  - `CacheProvider` (`teaf/_internal/contracts/cache.py`), espejo deliberado de `DatabaseProvider`: `connect`/`disconnect`/`health_check` más `get`/`set(ttl)`/`delete`/`ttl`/`ping`.
  - `InMemoryCacheProvider` — el **valor por defecto**, sin infraestructura desplegada, con purga amortizada que acota la memoria.
  - `RedisCacheProvider` — tras el extra opcional `pip install "teaf[redis]"`. **El import de `redis` es perezoso, dentro de `connect()`**: importar TEAF nunca requiere el paquete, que es lo que hace la dependencia realmente opcional y no opcional sobre el papel.
  - `CacheModule` abre el pool en `start()` y lo cierra en `dispose()`. Que exista el módulo no es burocracia: es lo único que garantiza que la conexión se cierre.
  - **Coste cero sin configurar**, verificado con benchmarks y no solo afirmado: no se construye el módulo, no se importa `redis`, y el camino de la petición es idéntico.
- **Los tres almacenes Redis pasan de preparados a implementados**: `RedisRateLimitStore`, `RedisQuotaStore` y `RedisIdempotencyStore` dejan de lanzar `NotImplementedError`. Se apoyan en `CacheProvider`, no en un cliente propio, para que el ciclo de vida de la conexión viva en un solo sitio. Punto de cableado: `ApiProtectionModule(cache_provider=...)`.
- **`api_trusted_proxies`** ([ADR-011](docs/architecture/adr/ADR-011-trusted-proxy-architecture.md)) — **cierra H-2**, que 2.9.2 solo pudo mitigar. Lista de IPs o redes CIDR (IPv4 e IPv6) de las que se acepta información de reenvío, comprobada contra la **IP de la conexión TCP**, que es el único dato que el cliente no puede falsificar.
  - Separa dos preguntas que el `trust_forwarded_headers` binario confundía en una: *¿hay un proxy delante?* y *¿viene **esta** petición de él?*
  - **La cadena `X-Forwarded-For` se recorre de derecha a izquierda.** Cada salto añade por la derecha, así que las entradas de la izquierda las pudo escribir el cliente: tomar la primera —la lectura ingenua, y la que hacía TEAF— es leer justo el trozo que el atacante controla.
  - **Falla cerrado**: una entrada inválida aborta el arranque. Una lista de confianza con una errata descartada en silencio es peor que no tener lista.
  - Los CIDR se parsean **al construir**, no por petición. Sin dependencias nuevas: `ipaddress` es librería estándar.
- **Longitud mínima del secreto JWT**, derivada del algoritmo según RFC 7518 §3.2 (HS256 ≥ 32 bytes, HS384 ≥ 48, HS512 ≥ 64). Se valida **al arrancar** en `Settings` y en `JWTProvider.__init__`, nunca durante una petición. El mensaje nombra algoritmo, longitud recibida y exigida, y **nunca el secreto**.
- **`teaf.cache`** — nueva fachada pública con 7 símbolos (`CacheProvider`, `CacheModule`, `CacheConfiguration`, `CacheBackend`, `InMemoryCacheProvider`, `RedisCacheProvider`, `RedisCacheConfiguration`). Se exporta el módulo, a diferencia de `DatabaseModule`/`SecurityModule`, por el mismo motivo que `ApiProtectionModule`: todo su valor está en que alguien abra la conexión al arrancar y la cierre al apagar.
- [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md) — matriz de compatibilidad de dependencias, y [`docs/modules/cache/CACHE.md`](docs/modules/cache/CACHE.md).
- **Pruebas de integración contra un Redis real** ([`tests/integration/test_cache_redis.py`](tests/integration/test_cache_redis.py)), que se **omiten** cuando no hay servidor para que la suite siga siendo ejecutable en cualquier máquina.

### Changed

- **`fastapi` 0.115.6 → 0.141.1** (`starlette` 0.41.3 → 1.4.1). Antes del upgrade se verificó estáticamente que TEAF **no usa ninguna API eliminada en starlette 1.0**: usa `lifespan=` y `app.add_exception_handler`, cero `on_event`/`on_startup`/`add_event_handler`. `httpx` solo es un extra de starlette, así que no fuerza httpx 2.
- **Ruptura de API pública** (`PUBLIC_API_VERSION` 1.0.0 → 2.0.0): los constructores de los tres almacenes Redis pasan de `(url, prefix)` a recibir un `CacheProvider`. **No puede romper a ningún consumidor**, porque hasta v0.9.2-alpha lanzaban `NotImplementedError` incondicionalmente: no existe una llamada que antes funcionara y ahora falle. La MAJOR sube igualmente porque [VERSIONING.md §5](docs/public-api/VERSIONING.md) manda subirla cuando el contrato cambia de forma incompatible, no cuando además duela. Tabla de migración en [MIGRATION-GUIDE.md §6](docs/public-api/MIGRATION-GUIDE.md#6-cuando-public_api_version-suba-de-major).
- **Ruptura de configuración asumida**: una aplicación con un secreto JWT por debajo del mínimo **deja de arrancar** al actualizar. Es intencionado — ese secreto era vulnerable a fuerza bruta, y seguir aceptándolo en silencio sería debilitar la política para mantener compatibilidad.
- `trust_forwarded_headers` queda **deprecado de hecho, no eliminado**: sigue funcionando igual y configurar `api_trusted_proxies` **silencia su aviso de arranque**, porque el aviso deja de describir un riesgo real.
- `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT` (renombrado en starlette 1.x; el código de estado no cambia).

### Fixed

- **El proveedor de Redis estaba roto para toda URL `redis://`** — es decir, para el backend por defecto. Se pasaba `ssl_cert_reqs` incondicionalmente a `from_url`, pero solo lo acepta `SSLConnection`: sobre una URL sin TLS reventaba con `TypeError` en la **primera operación**, no al conectar, porque `from_url` es perezoso. Lo destapó la suite de integración contra un Redis real; ninguna prueba con doble en memoria podía verlo. Corregido y fijado con una prueba unitaria que no necesita servidor.

### Security

- **`docs/security/accepted-vulnerabilities.json` queda vacío.** Las 7 vulnerabilidades de `starlette` que 2.9.2 tuvo que aceptar —porque `fastapi 0.115.6` fijaba `starlette<0.42.0`— desaparecen con el upgrade. Las entradas se **borran** en vez de dejarse marcadas como aceptadas: una excepción que ya no aplica es deuda invisible.
- Revisión de seguridad del sprint en [SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md): spoofing e inyección de cabeceras, credenciales y fugas de conexión de Redis, secretos débiles y mensajes de error de JWT.

### Known limitations

- **`RedisQuotaStore.consume` es un read-modify-write no atómico**: dos réplicas concurrentes pueden permitir un ligero exceso sobre la cuota. Documentado en su docstring, en [CACHE.md §10](docs/modules/cache/CACHE.md) y en el [backlog](docs/roadmap/BACKLOG.md). Se deja implementado y dicho, en vez de no ofrecer cuotas compartidas: un exceso ocasional acotado es un problema mucho menor que una cuota multiplicada por el número de réplicas.
- **Sigue sin haber un valor por defecto seguro** para las cabeceras de reenvío: sin configurar `api_trusted_proxies`, el comportamiento es idéntico a v0.9.2-alpha. El sprint aporta la posibilidad de configurarlo correctamente, no un valor por defecto distinto — el razonamiento de [ADR-010 §4](docs/architecture/adr/ADR-010-security-headers-and-forwarded-trust.md) sigue vigente.

## [0.9.2-alpha] - 2026-08-07

Sprint 2.9.2 — **Contrato de seguridad, puerta de release y cierre de la línea 2.9**. Cierra los tres pendientes que dejó abiertos Sprint 2.9.1. Sin funcionalidad de producto nueva.

**API pública sin rupturas**: 192 símbolos, 0 eliminados, 0 renombrados, 0 firmas rotas.

### Added

- **`SecurityHeadersMiddleware`** ([ADR-010](docs/architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)) — resuelve **H-1**. [SECURITY-STANDARD.md §7](docs/standards/SECURITY-STANDARD.md) exigía cuatro cabeceras y `Settings` declaraba tres campos para gobernarlas, pero **no existía nada que las emitiera**: un `security_headers_enabled: bool = True` que no activaba nada comunicaba una protección inexistente. Ahora `create_app` lo instala siempre y emite `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy` y `Strict-Transport-Security`, gobernados por los campos que ya existían.
  - Middleware **ASGI puro**, no `BaseHTTPMiddleware`: solo intercepta `http.response.start`, así que no materializa el cuerpo ni rompe el streaming. Coste medido: **ninguno** (memoria de construcción 192.1 → 192.4 KiB, arranque sin regresión).
  - **HSTS solo sobre HTTPS**, como exige RFC 6797 §7.2 — emitirla sobre HTTP la ignoran los navegadores y en desarrollo puede fijar `localhost` en HTTPS durante un año.
  - **La CSP no se aplica a `/docs` ni `/redoc`**: la política por defecto (`default-src 'none'`) dejaría Swagger UI en blanco, y un desarrollador que se lo encuentre así desactivará el middleware entero. Excepción acotada y documentada.
  - Nunca sobrescribe una cabecera ya presente: un proxy que también las añada no entra en conflicto.
  - **31 pruebas** que comprueban **valores reales** — incluidas respuestas de error, OpenAPI sin regresión y cuerpos byte a byte idénticos con el middleware activo y desactivado.
- **Campo nuevo** `security_content_security_policy` en `Settings` (aditivo). Su valor por defecto es el de una API JSON; una aplicación que sirva HTML propio debe sustituirlo.
- **Puerta de calidad `dependencies`** — cierra la laguna que Sprint 2.9.1 dejó documentada. `python -m pip_audit` sobre `requirements.txt`, con **excepciones explícitas y justificadas** en [`docs/security/accepted-vulnerabilities.json`](docs/security/accepted-vulnerabilities.json) (identificador, severidad, versión afectada, versión objetivo, justificación). Falla ante cualquier aviso no listado y lista los aceptados en cada ejecución, para que no se conviertan en deuda invisible. Las puertas pasan de 10 a **11**.
- **Pruebas anti-spoofing de cabeceras de reenvío** (13): demuestran de forma ejecutable que con `trust_forwarded_headers=False` un atacante **no** puede repartirse entre cubetas de rate limiting inventando IPs, y que con `True` sí — que es exactamente el riesgo de H-2.
- [`docs/security/SECURITY-CONFIGURATION.md`](docs/security/SECURITY-CONFIGURATION.md) — riesgo, valor por defecto y despliegue recomendado de `security_headers_enabled` y `api_trust_forwarded_headers`.

### Fixed

- **Ejecutar migraciones dejaba mudo al framework entero.** `database/migrations/env.py` llamaba a `logging.config.fileConfig()`, cuyo valor por defecto es `disable_existing_loggers=True`. Como `DatabaseInstaller` permite ejecutar migraciones dentro del proceso de la aplicación, arrancar con migraciones **desactivaba todos los loggers ya creados** — logging de peticiones, auditoría ([SECURITY-STANDARD.md §8](docs/standards/SECURITY-STANDARD.md)) y avisos de seguridad incluidos. El fallo es silencioso por naturaleza: nada falla, simplemente dejan de aparecer registros. Se descubrió porque desactivaba el logger del aviso de `trust_forwarded_headers`; 78 loggers quedaban desactivados en una ejecución completa de la suite. Corregido y fijado con una prueba de regresión.
- **`pyjwt` 2.10.1 → 2.13.0**: corrige **6 vulnerabilidades conocidas**, entre ellas un bypass de la lista blanca de algoritmos (PYSEC-2026-176) y confusión HMAC/JWK (PYSEC-2026-179). El análisis mostró que el código de TEAF ya las mitigaba por su cuenta, pero eso protege a TEAF, no a las aplicaciones construidas sobre él.
- **H-3**: comentario obsoleto en `_configuration_summary` que afirmaba que ningún campo de `Settings` es un secreto — falso desde Sprint 2.7. No había fuga (el resumen es una lista blanca), solo prosa desactualizada que describía la protección al revés.

### Changed

- [SECURITY-STANDARD.md §7](docs/standards/SECURITY-STANDARD.md) documenta ahora la implementación **real**: tabla de cabeceras, valores por defecto, configuración y las tres excepciones que hay que conocer. Ya no promete lo que el framework no hace.
- `trust_forwarded_headers` **mantiene su valor por defecto `True`** — invertirlo rompería silenciosamente a quien esté correctamente desplegado detrás de un proxy, convirtiendo su límite por IP en un límite global. Pero deja de ser silencioso: `ApiGateway.install()` avisa al arrancar cuando la confianza está activa y hay algún middleware que usa la IP del cliente. La solución completa (lista de proxies de confianza) queda en el backlog de Sprint 3.0.

### Security

Estado tras este Sprint en [SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md): **H-1 y H-3 resueltos**, **H-2 mitigado y documentado**, laguna de auditoría de dependencias **cerrada**.

Conviene decir explícitamente lo que esa última reveló: la revisión de Sprint 2.9.1 concluyó «versiones recientes, ningún aviso conocido». Al ejecutar `pip-audit` por primera vez aparecieron **13 avisos** en dos paquetes. Aquella conclusión era conocimiento, no verificación, y era incorrecta — que es precisamente el motivo por el que esta puerta existe ahora.

**Hallazgo nuevo (baja)**: TEAF no impone longitud mínima al secreto JWT. Lo destapó el `InsecureKeyLengthWarning` que introduce pyjwt 2.13.0. Imponerla cambiaría configuraciones que hoy funcionan; queda en el backlog.

## [0.9.1-alpha] - 2026-08-07

Sprint 2.9.1 — **Hardening, rendimiento y preparación para producción**. Sin funcionalidad nueva, sin módulos nuevos, sin cambios en la API pública y sin cambios de comportamiento: el objetivo era convertir lo que ya existía en algo desplegable. Estado completo en [docs/PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md).

**La API pública es 100% compatible con 0.9.0-alpha**, verificado de forma mecánica: 192 símbolos, 0 eliminados, 0 renombrados, 0 firmas rotas ([docs/BACKWARD-COMPATIBILITY.md](docs/BACKWARD-COMPATIBILITY.md)).

### Fixed

- **Fuga de memoria en los tres almacenes en memoria de protección de APIs** (`teaf/_internal/api/providers/memory.py`). Las entradas solo caducaban de forma perezosa —al consultar una clave concreta—, así que una clave que nunca se volvía a consultar no se liberaba nunca. El crecimiento no dependía del volumen de tráfico sino de su **cardinalidad** (IPs, claves de idempotencia, tenants), que es justo lo que un atacante controla. Corregido con purga amortizada cada 512 escrituras: **1.536 → 10 entradas retenidas (−99,3%)**, verificado en `tests/unit/test_memory_bounds.py`.
- **`otel_metrics.Gauge` no existe** (`observability/metrics/meter.py`): referencia a un símbolo inexistente que el tipado permisivo ocultaba. Ahora `otel_metrics._Gauge`.
- **Referencia obsoleta a un fichero eliminado** en `observability/exporters/prometheus.py`.

### Changed

- **Arranque 5,5× más rápido** (`Application()`: 15,50 → 2,82 ms; arranque ASGI completo: 18,42 → 5,79 ms; bootstrap de módulo: 17,96 → 6,25 ms; memoria de construcción: 290,7 → 192,1 KiB). El 97% del tiempo original lo consumía FastAPI generando modelos Pydantic de respuesta para los 30 endpoints de sistema. Se declaran ahora con `response_model=None` **y** con constantes explícitas de `responses=` (`teaf/_internal/shared/openapi.py`) que preservan el esquema OpenAPI: los cuerpos siguen siendo byte a byte idénticos. Detalle en [docs/PERFORMANCE.md](docs/PERFORMANCE.md).
- **`mypy --strict`: de 28 errores a 0** sobre 225 ficheros. La mayoría eran artefactos de invocar `mypy` en vez de `python -m mypy` —el ejecutable suelto no resolvía los tipos de FastAPI/Starlette y los degradaba a `Any`, ocultando errores reales—. Las puertas de calidad fijan ahora la invocación correcta.
- **Tipado de 11 middlewares**: `app: object` → `app: ASGIApp` (`starlette.types`).
- `black` deja de reformatear las migraciones generadas por Alembic (`force-exclude`, en paralelo a la exclusión que ya tenía `ruff`).
- [docs/standards/QUALITY-GATES.md](docs/standards/QUALITY-GATES.md) documenta la ejecución automática (nueva sección 0) sin duplicar los criterios, que siguen siendo la fuente de verdad.

### Added

- **Puertas de calidad en un solo comando**: `python scripts/quality_gates.py` ejecuta las 10 puertas automatizables (formato, lint, tipos, ciclos, espacio de nombres, frontera pública, compatibilidad de firmas, arranque real, pruebas con cobertura, benchmarks) con `--fast`, `--list` y `--gate`.
  - `scripts/check_runtime_startup.py` — la única puerta que **ejecuta** el framework de extremo a extremo: construye una `Application`, corre el ciclo de vida ASGI, llama a los 7 endpoints de sistema y la apaga. Ningún análisis estático detecta un fallo de cableado.
  - `scripts/check_circular_dependencies.py` — AST + DFS tricolor: **0 ciclos en 225 módulos**.
  - `scripts/check_public_api_surface.py` — captura y compara **firmas**, no solo nombres, contra `docs/public-api/api-surface.json`, distinguiendo rupturas de ampliaciones.
- **Suite de benchmarks** ([`benchmarks/`](benchmarks/README.md)): 25 benchmarks en 8 suites, con baseline versionada y detección de regresiones. Sus tres reglas de comparación —mínimo en vez de mediana, umbral del 60%, suelo absoluto de 1 µs— salen de medir la varianza real de la suite, no de números elegidos a ojo; y una regresión se **vuelve a medir** antes de reportarse, porque un pico del anfitrión llegó a multiplicar por 2,5 un resultado sin cambio de código. Cifras en [docs/BENCHMARKS.md](docs/BENCHMARKS.md).
- **Pruebas de carga** ([`loadtests/`](loadtests/README.md)): 9 escenarios concurrentes con throughput, latencias p50/p95/p99, CPU, memoria y errores. **0 errores** en 9 × 2.000 peticiones. Cada escenario tiene su control explícito para que la resta signifique algo.
- **Documentación de producción**: [PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md), [PERFORMANCE.md](docs/PERFORMANCE.md), [BENCHMARKS.md](docs/BENCHMARKS.md), [BACKWARD-COMPATIBILITY.md](docs/BACKWARD-COMPATIBILITY.md) y [SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md).
- **52 pruebas nuevas** (1.074 → 1.126, cobertura **98%**): límites de memoria, esquemas OpenAPI y comparación de benchmarks.

### Removed

- **7 módulos de código muerto**, ninguno alcanzable desde `teaf.*`: `shared/{collections,dates,strings,validation}.py` y `providers/telemetry/{logger,metrics,tracer}_provider.py`. Estos últimos ya los declaraba muertos [ADR-008](docs/architecture/adr/ADR-008-enterprise-observability-stack.md) («todos abstractos, ninguno instanciado en ningún sitio») y además colisionaban por nombre con el `TracerProvider` real de OpenTelemetry.
- `is_valid_uuid` de `shared/identifiers.py` — sin uso.

### Security

Revisión completa en [docs/SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md). **Ningún hallazgo se corrigió en código**, deliberadamente: este Sprint tenía prohibido añadir funcionalidad o cambiar comportamiento, y corregir en silencio un hallazgo de seguridad dentro de un Sprint de endurecimiento sería el tipo de cambio no revisado que la revisión existe para evitar.

- **Alta** — Las cabeceras de seguridad HTTP que [SECURITY-STANDARD.md §7](docs/standards/SECURITY-STANDARD.md) exige **no están implementadas**: los campos `security_headers_enabled`/`security_hsts_max_age_seconds`/`security_frame_options` de `Settings` no los lee nadie y no existe ningún `SecurityHeadersMiddleware`. Un valor por defecto de `True` comunica una protección inexistente.
- **Media** — `trust_forwarded_headers` vale `True` por defecto: expuesta directamente a internet, una aplicación puede saltarse cualquier límite por IP falsificando `X-Forwarded-For`.
- **Baja** — Comentario obsoleto sobre secretos en `_configuration_summary`; `pydantic` declarada sin importarse directamente.
- **Verificado sin hallazgos**: verificación de JWT (algoritmo en lista blanca, `aud`/`iss`, `leeway`), API Keys (256 bits, HMAC con pepper, búsqueda por hash), criptografía (`compare_digest`, `secrets`), y **ausencia de fuga de secretos** por los 12 endpoints de sistema, comprobada con valores centinela.
- **Laguna conocida**: sin `pip-audit`/`safety` en el entorno, el árbol de 18 dependencias no se ha contrastado contra una base de datos de vulnerabilidades.

## [0.9.0-alpha] - 2026-08-07

### Added

- **Enterprise API Protection Platform** (Sprint 2.9, [ADR-009](docs/architecture/adr/ADR-009-enterprise-api-protection.md)): rate limiting, cuotas, CORS, versionado de API, validación de borde, compresión, idempotencia y auditoría — ocho subsistemas independientes que un único `ApiGateway` compone en una cadena de middlewares con una sola llamada. Ver [docs/api/API-PROTECTION.md](docs/api/API-PROTECTION.md).
  - **Nuevo subsistema `teaf/_internal/api/`** (antes solo un `README.md` de intención): `gateway/`, `middleware/`, `ratelimit/`, `quotas/`, `cors/`, `versioning/`, `validation/`, `compression/`, `idempotency/`, `audit/`, `providers/` y `module/`, más `models.py` (modelo de dominio compartido) y `exceptions.py`.
  - **Rate limiting**: los cuatro algoritmos completos (`FixedWindowAlgorithm`, `SlidingWindowAlgorithm`, `TokenBucketAlgorithm`, `LeakyBucketAlgorithm`), implementados como **funciones puras sobre el estado** —sin I/O, sin reloj propio, sin conocer el almacén—, lo que permite probar los bordes de ventana sin dormir ni levantar infraestructura. Configurables por usuario, API Key, tenant, IP, endpoint y rol (`ProtectionScope`), con filtrado por prefijo de endpoint y por rol, ráfaga (`burst`) y coste por petición.
  - **Quotas**: `QuotaManager` con las cuatro magnitudes de `QuotaKind` (peticiones, ancho de banda, payload, concurrencia) y los cuatro períodos de `QuotaPeriod` (minuto/hora/día/mes). El índice de ventana viaja en la clave de almacén, así que el consumo se reinicia solo al cambiar de período, sin ningún job de reinicio. Las cuotas de concurrencia suben al entrar y bajan en un `finally`.
  - **CORS**: `CorsPolicy` propia (en vez de `CORSMiddleware` de Starlette) por dos razones concretas: ser un objeto de dominio inspeccionable y componible, y soportar comodines de subdominio (`https://*.torus.com`). Aplica sola la regla del estándar de nunca combinar credenciales con `Access-Control-Allow-Origin: *`, y añade `Vary: Origin` siempre.
  - **Versionado de API**: `ApiVersionNegotiator` con las tres estrategias (URI, cabecera y tipo de medio) en el orden de prioridad configurado, versión por defecto, modo estricto y deprecación vía las cabeceras estándar `Deprecation`/`Sunset`. Deja el resultado en `request.state.api_version` y **no enruta**: eso lo decide la aplicación.
  - **Validación de borde**: `RequestValidator` sobre metadatos (tamaño, tipo de contenido, cabeceras obligatorias, agente de usuario, longitud de URL) — evaluada antes de que la petición llegue al endpoint, complementando sin solaparse la validación de payload de Pydantic. Incluye validación de tamaño de respuesta, desactivada por defecto.
  - **Compresión**: `GzipCompressionProvider` sobre la librería estándar (siempre disponible) y `BrotliCompressionProvider` sobre un paquete **opcional** (`brotli`/`brotlicffi`) — sin dependencia dura nueva. `CompressionNegotiator` respeta la preferencia del cliente (`Accept-Encoding` con factores `q`), un umbral mínimo de tamaño y una lista de tipos comprimibles, y devuelve el original si comprimir no reduce el tamaño.
  - **Idempotencia**: `IdempotencyManager` con clave de cliente (`Idempotency-Key`), huella SHA-256 de método+ruta+cuerpo, detección de reintentos, reproducción exacta de la respuesta original (`X-Idempotent-Replay`) y conflicto (`409`) al reutilizar una clave con otro cuerpo. Nunca guarda respuestas 5xx.
  - **Auditoría de API**: `ApiAudit` + `ApiAuditRecord` con método, ruta, código, latencia, identidad, tenant, API Key, correlation/trace/span-id, IP de origen, versión de API y tamaños. Varios destinos a la vez (`InMemoryAuditSink`, `LoggingAuditSink`, o uno propio); un destino que falle no impide que los demás reciban el registro. **Nunca se muestrea**, a diferencia de las trazas.
  - **8 middlewares ASGI** (`RateLimitMiddleware`, `QuotaMiddleware`, `CorsMiddleware`, `ApiVersionMiddleware`, `RequestValidationMiddleware`, `CompressionMiddleware`, `IdempotencyMiddleware`, `ApiAuditMiddleware`), compatibles con `SecurityMiddleware` (Sprint 2.7) y `ObservabilityMiddleware` (Sprint 2.8). `ApiGateway.install(app)` los monta en el orden correcto, fijado y justificado en `MIDDLEWARE_ORDER`.
  - **`ApiProtectionModule`**: cuarto módulo real construido sobre el Module SDK, con `ApiProtectionConfiguration`, `ApiProtectionHealth` y 9 capacidades / 7 servicios / 8 eventos declarados en su manifiesto. Registra automáticamente en el contenedor de dependencias `ApiGateway`, `RateLimiter`, `QuotaManager`, `ApiAudit`, `RequestValidator`, `IdempotencyManager` y `CompressionProvider` — solo los de subsistemas realmente configurados.
  - **Eventos**: `request.accepted`, `request.rejected`, `rate.limit.exceeded`, `quota.exceeded`, `idempotency.detected`, `request.compressed`, `audit.recorded`, `version.negotiated` — vía `EventBus`.
  - **Contratos** (`teaf/_internal/contracts/api.py`): `RateLimitStore`, `QuotaStore`, `IdempotencyStore`, `AuditSink`, `CompressionProvider` y `ApiProtectionPolicy` (preparado para delegar en un gateway externo). Implementación **en memoria por defecto** — la plataforma funciona sin infraestructura desplegada — y variante **Redis preparada** (`RedisRateLimitStore`/`RedisQuotaStore`/`RedisIdempotencyStore`), que documenta qué comando implementa cada operación y lanza `NotImplementedError` explícito hasta que un ADR apruebe `redis-py`.
  - **`ModuleCategory.API` y `CapabilityCategory.API`**: nuevas categorías (aditivas) + su `ModuleTemplate` en `MODULE_TEMPLATES`.
  - **API pública `teaf.api`** (`teaf/api.py`, 78 símbolos, reexportados también desde `teaf`): `ApiGateway`, `RateLimiter`, `QuotaManager`, `CorsPolicy`, `ApiVersion`, `RequestValidator`, `CompressionProvider`, `IdempotencyManager`, `ApiAudit` y `ApiProtectionModule`, más sus reglas, políticas, decisiones, algoritmos, almacenes, middlewares y excepciones.
  - **Nuevas Settings** (`Settings`, prefijo `api_`): 46 campos cubriendo rate limiting, quotas, CORS, versionado, validación, compresión, idempotencia, auditoría y `api_trust_forwarded_headers`. `ApiProtectionConfiguration.from_mapping` reconoce el prefijo, así que `from_mapping(settings.model_dump())` funciona sin transformar nada. `ProductionSettings` activa `api_audit_logging_sink_enabled` por defecto.
  - **7 ejemplos ejecutables** en `examples/`: `rate-limiting`, `quota-management`, `api-versioning`, `cors-policy`, `response-compression`, `idempotent-requests`, `api-audit` — todos vía la API pública exclusivamente, verificados por `scripts/check_public_api_boundary.py`.
  - **7 documentos nuevos** en `docs/api/`: `API-PROTECTION.md`, `RATE-LIMITING.md`, `QUOTAS.md`, `VERSIONING.md`, `CORS.md`, `IDEMPOTENCY.md`, `AUDIT.md`. Actualizados: `README.md`, `CLAUDE.md`, `docs/public-api/PUBLIC-API.md` (nueva sección 8), `docs/public-api/IMPORT-GUIDE.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/MODULE-CATALOG.md`, `docs/roadmap/ROADMAP.md`, `docs/roadmap/BACKLOG.md`, `examples/README.md`.
  - **290 pruebas nuevas** cubriendo los cuatro algoritmos (incluidos bordes de ventana, recarga, desbordamiento y TTL), las seis dimensiones, las cuatro magnitudes de cuota y los cuatro períodos, CORS (comodines de subdominio, credenciales, preflight), versionado (las tres estrategias, deprecación, modo estricto), validación (413/415/400/500), compresión (negociación, umbral, Brotli disponible y ausente), idempotencia (reproducción, conflicto, TTL, 5xx), auditoría (destinos, fallos de destino, los cuatro desenlaces), el registro en DI, la integración con el Runtime y 42 pruebas de integración HTTP de la cadena completa. Suite: **1.065 pruebas** (775 + 290 nuevas), **97% de cobertura** del subsistema nuevo.

### Changed

- `ApplicationException` (`core/exceptions.py`) gana un atributo de clase opcional `http_status` (`None` por defecto, comportamiento idéntico al anterior). Es el punto de extensión declarativo que permite a jerarquías definidas fuera de `core/` usar códigos que su mapeo por categoría no cubría (429/413/415/409), sin que `middleware/exception_handler.py` tenga que importar ningún subsistema.
- `middleware/exception_handler.py` expone `build_problem_response()`, para que los middlewares que rechazan una petición **antes** de `call_next` —que nunca alcanzan los manejadores registrados con `app.add_exception_handler`, por cómo Starlette ordena su pila— emitan exactamente el mismo cuerpo RFC 7807 que emitiría el manejador central.
- **`ApiProtectionModule` es el único módulo real que TEAF expone públicamente**, a diferencia de `DatabaseModule`/`SecurityModule`/`ObservabilityModule`. Excepción deliberada y documentada a `PUBLIC-API.md` §9: la protección de APIs se activa como una unidad, y obligar a recomponerla pieza a pieza en cada aplicación sería repetición sin ganancia de desacoplamiento. Ver [ADR-009](docs/architecture/adr/ADR-009-enterprise-api-protection.md), "Decisiones de ubicación y superficie".
- `pyproject.toml` añade `UP042` a `[tool.ruff.lint].ignore`. La regla ("hereda de `str` y `Enum`, usa `enum.StrEnum`") empezó a aparecer al actualizarse ruff, sobre las ~27 enumeraciones que TEAF escribe así **desde el Sprint 2.2**: 20 de ellas ya la incumplían en `HEAD` antes de este Sprint. Migrar a `StrEnum` cambiaría el resultado de `str(miembro)` en serialización, logs y respuestas HTTP — un cambio de comportamiento transversal que exige su propio ADR ([CLAUDE.md](CLAUDE.md) §12), no un efecto colateral de un Sprint funcional.

### Fixed

- Dos violaciones de longitud de línea preexistentes (`contracts/telemetry.py`, `observability/health/checker.py`) que `ruff check .` reportaba desde antes de este Sprint.

### Notes

- **Compatibilidad hacia atrás completa**: ningún símbolo público existente cambia de nombre, firma ni comportamiento. Toda la funcionalidad del Sprint 2.9 es aditiva; las 775 pruebas anteriores siguen pasando sin modificaciones de comportamiento (solo se actualizaron tres asserts de número de versión y uno del recuento de plantillas de módulo).
- **Limitación conocida y documentada**: los proveedores de almacenamiento en memoria son por proceso. En un despliegue multi-instancia cada réplica aplica sus propios límites, así que el límite efectivo es el configurado × número de réplicas. La arquitectura queda preparada para Redis sin rediseño — ver [docs/api/API-PROTECTION.md](docs/api/API-PROTECTION.md), §10.
- **Coste asumido**: los middlewares de compresión, idempotencia y validación de respuesta materializan el cuerpo completo de la respuesta, renunciando al streaming real en las rutas que atraviesan. Por eso la validación de respuesta viene desactivada por defecto.
- **Cero dependencias nuevas**: toda la plataforma se construye sobre la librería estándar y sobre lo que TEAF ya declaraba en [STACK.md](docs/architecture/STACK.md). Brotli es opcional y degrada silenciosamente cuando no está instalado.

## [0.8.0-alpha] - 2026-08-04

### Added

- **Enterprise Observability Platform** (Sprint 2.8, [ADR-008](docs/architecture/adr/ADR-008-enterprise-observability-stack.md)): logging estructurado, tracing distribuido, métricas, health checks compuestos y diagnóstico agregado del Runtime, construidos alrededor de OpenTelemetry como motor único — nunca reinventado por debajo. Ver [docs/observability/OBSERVABILITY.md](docs/observability/OBSERVABILITY.md).
  - **Correlación end-to-end**: `core/context.py` extendido aditivamente con trace-id/span-id/user-id/tenant-id (mismo patrón `ContextVar` que el correlation-id existente desde Sprint 2.1) — `OtelTracer.start_span()` sincroniza trace/span-id automáticamente al abrir/cerrar cada span; `SecurityMiddleware` (vía `set_security_context()`) sincroniza user-id/tenant-id al resolver identidad. `JsonFormatter` (`core/logging.py`) incluye los cinco identificadores en cada log — `null`/`"-"` cuando no aplican, nunca omitidos — sin que `core/` conozca `security/`/`observability/` (regla de capas de FRAMEWORK-BLUEPRINT.md).
  - **Tracing distribuido**: `Tracer`/`Span` (contratos) + `OtelTracer`/`OtelSpan` (implementación sobre `opentelemetry.trace`) — spans padre/hijo automáticos vía propagación de contexto, `links` entre trazas causalmente relacionadas, atributos, eventos, excepciones (`record_exception`) y estado (`SpanStatus`). `ObservabilityMiddleware` abre un span `SERVER` por petición HTTP y registra su duración.
  - **Métricas**: `Meter`/`Counter`/`UpDownCounter`/`Histogram`/`Gauge` (contratos) + `OtelMeter` y sus cuatro instrumentos (implementación sobre `opentelemetry.metrics`).
  - **Exportadores**: `ConsoleExporter`, `OtlpExporter`, `PrometheusExporter` completamente implementados; `JaegerExporter`/`ZipkinExporter`/`DynatraceExporter`/`ElasticExporter`/`AzureMonitorExporter`/`GrafanaExporter`/`DatadogExporter`/`NewRelicExporter`/`SplunkExporter` preparados (contrato `Exporter` cumplido, alcanzables hoy vía `OtlpExporter` + un Collector, `NotImplementedError` explícito si se usan directamente).
  - **Health compuesto**: `CompositeHealthChecker` cierra la brecha documentada desde Sprint 2.5 ("ningún endpoint invoca estas funciones todavía") — agrega el `ModuleHealth` de cada módulo bootstrapeado; `/health`/`/ready` de `Application` ya lo consumen (peor estado crítico gana; `/ready` devuelve `503` solo si algo crítico está `UNHEALTHY`); `/live` sigue sin evaluar dependencias, a propósito.
  - **Runtime Diagnostics**: memoria RSS y CPU reales en `RuntimeDiagnostics` (antes placeholders `"not-implemented"`, vía `resource.getrusage()`, sin dependencia nueva); `build_diagnostic_report()` envuelve `RuntimeDiagnostics` + `HealthReport` agregado en un `DiagnosticReport` único.
  - **`ObservabilityModule`**: el módulo SDK que empaqueta toda la plataforma (`teaf/_internal/modules/observability/`) — tercer módulo real construido sobre el Module SDK (tras `DatabaseModule`/`SecurityModule`), con `ObservabilityConfiguration`, `ObservabilityHealth` y 4 capacidades/2 servicios/6 eventos declarados en su manifiesto. No se expone públicamente (mismo criterio que `DatabaseModule`/`SecurityModule`). Deliberadamente no fija el `TracerProvider`/`MeterProvider` globales de OpenTelemetry (varias instancias conviven en el mismo proceso, p. ej. en tests).
  - **Eventos**: `trace.started`, `trace.finished`, `metric.recorded` (`ObservabilityMiddleware`), `health.changed` (`ObservabilityModule.start()`), `export.completed` (`ObservabilityModule.dispose()`), `diagnostic.generated` (`build_diagnostic_report()`) — vía `EventBus`.
  - **`ModuleCategory.OBSERVABILITY`**: nueva categoría de módulo (aditiva) + su `ModuleTemplate` en `MODULE_TEMPLATES`.
  - **API pública `teaf.observability`** (`teaf/observability.py`, 43 símbolos, reexportados también desde `teaf` de nivel superior): `Tracer`, `Span`, `Meter`, `Counter`, `UpDownCounter`, `Histogram`, `Gauge`, `Exporter`, `TelemetryProvider`, sus implementaciones `Otel*`, los 12 exportadores, `SpanKind`/`SpanStatus`, `HealthCheck`/`HealthReport`/`HealthStatus`, `CompositeHealthChecker`, `DiagnosticReport`/`build_diagnostic_report`, `get_logger`, `TraceContext`/`TelemetryContext` y sus funciones, `ObservabilityMiddleware`.
  - **Nuevas Settings** (`teaf._internal.config.settings.Settings`): `observability_service_version`, `observability_tracing_enabled`/`observability_metrics_enabled`, `observability_sampling_ratio`, `observability_console_exporter_enabled`, `observability_otlp_*` (exporter/endpoints/timeout), `observability_prometheus_*` (exporter/prefix), `observability_metrics_export_interval_millis`. `configure_logging()`/`JsonFormatter` ganan un parámetro `environment` (aditivo, `"development"` por defecto).
  - **6 ejemplos ejecutables** en `examples/`: `structured-logging`, `distributed-tracing`, `metrics`, `health-checks`, `prometheus-metrics`, `opentelemetry-otlp` — todos vía la API pública exclusivamente, verificados por `scripts/check_public_api_boundary.py` y ejecutados como subprocesos reales en `tests/integration/test_teaf_examples.py`.
  - **7 documentos nuevos** en `docs/observability/`: `OBSERVABILITY.md`, `LOGGING.md`, `TRACING.md`, `METRICS.md`, `HEALTH.md`, `EXPORTERS.md`, `OPENTELEMETRY.md`. Actualizados: `README.md`, `docs/public-api/PUBLIC-API.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/MODULE-CATALOG.md`, `docs/architecture/STACK.md`.
  - **105 pruebas nuevas** cubriendo modelo de dominio, tracing (spans padre/hijo, links, excepciones), métricas (los cuatro instrumentos), exportadores (los 3 implementados + los 9 preparados), `CompositeHealthChecker` (agregación, checks críticos/no críticos, excepciones), `ObservabilityConfiguration`, `build_diagnostic_report`, enriquecimiento de logging (trace/span/user/tenant/environment/module/capability), la fachada pública `teaf.observability`, integración end-to-end del `ObservabilityModule` contra `Application`/`Runtime` reales, y los 6 ejemplos nuevos ejecutándolos como subprocesos reales. Suite completa: 775 pruebas (670 + 105 nuevas).

### Fixed

- `_INFRASTRUCTURE_MODULES` (`teaf/_internal/core/application.py`) registraba un placeholder `"telemetry"` (`CONTRACTS_ONLY`, heredado de Sprint 2.2) que ya no aportaba nada distinto una vez que `ObservabilityModule` cubre ese subsistema bajo el nombre real `"observability"` — retirado (mismo criterio que ya aplica a `"database"`/`"security"` desde Sprints 2.6/2.7).
- `HealthCheck.check` (`observability/models.py`) estaba tipado como no-opcional pese a que `CompositeHealthChecker` siempre necesitó aceptar `None` (un `ModuleHealth` sin `check` declarado) — corregido a `Callable[[], CapabilityHealth] | None`.

### Notes

- Compatibilidad hacia atrás completa: ningún símbolo público existente cambia de nombre, firma ni comportamiento. `TelemetryProvider` (contrato mínimo de Sprint 2.2) se mantiene sin cambios; `TelemetryContext`/`set_telemetry_context`/`get_telemetry_context` conservan su forma y comportamiento — ahora delegan en `core/context.py` en vez de mantener su propio `ContextVar`, de forma transparente para quien los consume.
- `/health` y `/ready` cambian de forma (nuevos campos `modules`/`checks` en la respuesta) pero no de contrato de status code para el caso ya cubierto por tests previos (sin módulos registrados, siguen respondiendo `200`) — un consumidor que solo comprobaba el status code no se ve afectado; uno que dependía de la forma exacta del JSON debe adaptarse (documentado en `docs/observability/HEALTH.md`).
- La arquitectura permite añadir Dynatrace/Elastic/Azure Monitor/Grafana/Datadog/New Relic/Jaeger/Zipkin/Splunk nativos en el futuro sin rediseño — implementar `configure_tracing`/`configure_metrics` en su `PreparedExporter` correspondiente es aditivo (ver ADR-008, sección Consecuencias).

## [0.7.0-alpha] - 2026-08-04

### Added

- **Enterprise Security Platform** (Sprint 2.7, [ADR-007](docs/architecture/adr/ADR-007-enterprise-security-stack.md)): autenticación y autorización empresarial completas, diseñadas alrededor del contrato `IdentityProvider` — nunca acopladas a JWT ni a ningún mecanismo concreto. Ver [docs/security/SECURITY-ARCHITECTURE.md](docs/security/SECURITY-ARCHITECTURE.md).
  - **Cinco Identity Providers implementados**: Anonymous (respaldo, siempre disponible), JWT (`JWTProvider`/`JWTIdentityProvider`, access+refresh, revocación, rotación con revocación-en-reutilización, clock skew configurable), API Key (`ApiKeyProvider`/`ApiKeyIdentityProvider`, transporte por header/query string, hashing HMAC-SHA256, expiración, revocación, scopes, rotación), LDAP/Active Directory (`LDAPProvider`, bind + búsqueda de grupos + mapeo a roles/permisos, vía `ldap3` en threadpool), Azure AD/Microsoft Entra ID (`AzureADProvider`, OIDC + JWKS + Authorization Code Flow, multi-tenant con lista de tenants permitidos).
  - **`OpenIDConnectProvider`**: base OIDC genérica y reutilizable de la que `AzureADProvider` es la primera especialización — Keycloak/Auth0/Okta/Google se añadirían como subclases sin tocar `SecurityMiddleware` ni ningún otro proveedor. Contratos preparados y deliberadamente sin implementación para OAuth2 no-OIDC (`OAuth2IdentityProvider`, pensado para GitHub/Apple) y SAML (`SAMLIdentityProvider`).
  - **RBAC + políticas**: `Role`/`Permission` (reutilizados de Sprint 2.2), `StaticRoleResolver`, `RolePermissionResolver`, `PrincipalResolver`, `Policy`/`DefaultPolicyEvaluator` para reglas arbitrarias que un rol/permiso plano no puede expresar (p. ej. pertenencia a tenant).
  - **Modelo de dominio**: `Claims`, `Identity`, `Principal`, `AuthenticationCredentials`/`AuthenticationResult`, `TokenPair` (`teaf._internal.security.models`) — `SecurityContext` (Sprint 2.2) extendido aditivamente con `identity`/`principal`/`tenant_id`/`provider_id`/`correlation_id`/`request_id`.
  - **Criptografía**: `Argon2PasswordHasher` (por defecto, OWASP) y `BcryptPasswordHasher` (alternativo) implementando `PasswordHasher`; `HmacCryptoProvider` (firmas HMAC-SHA256 con rotación de claves) implementando `CryptoProvider`.
  - **`SecurityMiddleware`**: resuelve identidad en cada petición ("sniffing" de `Authorization: Bearer` hacia `jwt`/`azure-ad` según el `iss` sin verificar, `Basic` hacia `ldap`, `X-API-Key`/`?api_key=` hacia `api-key`), publica el `SecurityContext` en un `ContextVar` — nunca bloquea una petición por falta de autenticación. Publica `authentication.started`/`succeeded`/`failed` vía `EventBus`.
  - **`@authorize()`/`@allow_anonymous()`**: decoradores de autorización declarativa por endpoint (`role=`/`permission=`/`policy=`, funcionan en endpoints síncronos y `async def`) — `teaf._internal.security.decorators`.
  - **Dependencias de FastAPI**: `current_identity`/`current_principal`/`current_claims`/`current_security_context` — leen el `SecurityContext` de la petición en curso vía `Depends(...)`.
  - **`SecurityModule`**: el módulo SDK que empaqueta toda la plataforma (`teaf/_internal/modules/security/`) — segundo módulo real construido sobre el Module SDK (tras `DatabaseModule`), con `SecurityConfiguration`, `SecurityHealth` y 5 capacidades/3 servicios/12 eventos declarados en su manifiesto. No se expone públicamente (mismo criterio que `DatabaseModule`) — una aplicación compone la plataforma directamente vía `teaf.security`.
  - **API pública `teaf.security`** (`teaf/security.py`, 52 símbolos, reexportados también desde `teaf` de nivel superior): `SecurityContext`, `Identity`, `Principal`, `Claims`, `Role`, `Permission`, `Policy`, `IdentityProvider`, `JWTProvider`, `ApiKeyProvider`, `LDAPProvider`, `AzureADProvider`, `AuthenticationProvider`, `AuthorizationProvider`, `PasswordHasher`, `CryptoProvider`, `authorize`, `allow_anonymous`, `current_identity`/`current_principal`/`current_claims`/`current_security_context`, y sus compañeros necesarios (`IdentityProviderRegistry`, `SecurityMiddleware`, resolutores RBAC, tiendas de revocación/API Key, etc.).
  - **Nuevas Settings** (`teaf._internal.config.settings.Settings`): JWT (secret/algorithm/issuer/audience/TTLs/clock skew), API Keys (header/query param/hash secret), LDAP (server/base DN/user DN template/group search), Azure AD (tenant/client id/secret/allowed tenants), Multi Tenant, política de contraseñas (hasher/costes Argon2/rounds BCrypt, reducidos automáticamente en `TestingSettings`), rotación de secretos (activada por defecto en `ProductionSettings`), cabeceras de seguridad HTTP.
  - **8 ejemplos ejecutables** en `examples/`: `jwt-login`, `api-key-auth`, `ldap-login`, `azure-ad-login`, `role-based-endpoint`, `permission-based-endpoint`, `policy-based-endpoint`, `anonymous-endpoint` — todos vía la API pública exclusivamente, verificados por `scripts/check_public_api_boundary.py` y ejecutados como subprocesos reales en `tests/integration/test_teaf_examples.py`.
  - **7 documentos nuevos** en `docs/security/`: `SECURITY-ARCHITECTURE.md`, `JWT.md`, `APIKEY.md`, `LDAP.md`, `AZURE-AD.md`, `RBAC.md`, `CLAIMS.md`. Actualizados: `README.md`, `docs/public-api/PUBLIC-API.md`, `docs/public-api/PACKAGE-STRUCTURE.md`, `docs/public-api/IMPORT-GUIDE.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/MODULE-CATALOG.md`, `docs/standards/SECURITY-STANDARD.md`.
  - **151 pruebas nuevas** (135 de la plataforma de seguridad propiamente dicha, cubriendo modelo de dominio, criptografía, JWT, API Keys, los 5 Identity Providers —LDAP con conexión falsa inyectada, Azure AD con `httpx.MockTransport` y un JWT RS256 real firmado en la prueba—, RBAC/políticas, `SecurityMiddleware` de extremo a extremo, decoradores, dependencias de FastAPI, `SecurityModule`, Settings y la fachada pública; más 16 pruebas que verifican los 8 ejemplos nuevos ejecutándolos como subprocesos reales) — 96% de cobertura de la plataforma de seguridad. Suite completa: 670 pruebas (519 + 151 nuevas).

### Fixed

- `_INFRASTRUCTURE_MODULES` (`teaf/_internal/core/application.py`) registraba un placeholder `"security"` (`CONTRACTS_ONLY`, heredado de Sprint 2.2) en el mismo `ModuleRegistry` que usa `Application(modules=[...])` — colisionaba por nombre con cualquier `SecurityModule` real, impidiendo registrarlo. Retirado, ahora que Sprint 2.7 entrega la implementación real (mismo criterio que ya aplica a `"database"` desde Sprint 2.6).

### Notes

- Compatibilidad hacia atrás completa: ningún símbolo público existente cambia de nombre, firma ni comportamiento. `AuthenticationProvider`/`AuthorizationProvider` (contratos mínimos de Sprint 2.1) se mantienen sin cambios. `SecurityContext` se extiende solo de forma aditiva (todos los campos nuevos con valor por defecto).
- La plataforma está lista para OAuth2 genérico/OIDC genérico/Keycloak/Auth0/Okta/Google/SAML sin rediseño arquitectónico — ver sección 5 de `docs/security/SECURITY-ARCHITECTURE.md`.

## [0.6.3-alpha] - 2026-08-04

### Added

- **Module Registration API** (Sprint 2.6.3, cierre de la serie Sprint 2.6): registrar módulos usando exclusivamente la API pública — sin conocer el `Runtime`, sin llamar a `module.bootstrap()` a mano, sin `asyncio.run()`, sin threads.
  - `Application(modules=[...])`: nuevo parámetro (keyword-only) del constructor — los módulos pasados arrancan automáticamente cuando arranca el ciclo de vida ASGI de la aplicación.
  - `Application.add_module(module) -> Application`: forma encadenable equivalente (`Application().add_module(A()).add_module(B())`).
  - Toda la orquestación vive en el composition root (`teaf/_internal/core/application.py`, `_lifespan`): arranca los módulos pendientes justo después de `runtime.startup()`, en orden de registro, y los apaga en orden inverso antes de `runtime.shutdown()` — el `Runtime` en sí no cambia (mantiene su dependencia de una sola vía hacia `sdk/`, nunca al revés, evitando un ciclo real con `ModuleContext`).
  - Errores existentes (`ModuleRegistrationException` por duplicados, `ModuleValidationException` por manifiestos inválidos) se siguen lanzando igual, ahora disparados por el arranque del ciclo de vida en vez de por una llamada manual — mismo contrato de errores.
  - Nuevo ejemplo `examples/module-registration/` (4º ejemplo de `examples/`): registra un módulo con `Application(modules=[HelloModule()])` y dispara el ciclo de vida con `TestClient`, sin bootstrap manual.
  - 18 pruebas nuevas (`tests/unit/test_module_registration.py`): constructor con 0/1/N módulos, `.add_module()` encadenado, orden de arranque/apagado, integración con `Runtime`/`CapabilityRegistry`, duplicados, manifiestos inválidos, ciclo de vida (`READY`/`DISPOSED`). Suite completa: 519 pruebas.
  - Documentación: nueva sección "Registrar módulos" en `docs/public-api/PUBLIC-API.md`; guía de migración (bootstrap manual → `Application(modules=[...])`) en `docs/public-api/MIGRATION-GUIDE.md`; nota cruzada en `docs/sdk/SDK.md`.

### Notes

- Compatibilidad hacia atrás completa: `Application()` sin argumentos, `create_app(settings)` posicional y todo el resto de la API pública (`Runtime`, `ModuleRegistry`, `CapabilityRegistry`, `ServiceContainer`, `PluginLoader`, `ModuleBase.bootstrap()`/`.shutdown()` manuales) siguen funcionando exactamente igual — ninguna capacidad existente se elimina ni cambia de comportamiento.

## [0.6.2-alpha] - 2026-08-04

### Changed

- **Internal Namespace Refactor** (Sprint 2.6.2): el paquete privado `backend/` (127 archivos, 12 subpaquetes reales más 10 directorios reservados) se mueve íntegramente a `teaf/_internal/`, como subpaquete privado de `teaf` en vez de paquete de nivel superior independiente — elimina por construcción el riesgo de colisión de namespace con un posible paquete `backend/` propio de una aplicación consumidora (resolución de imports dependiente del orden de `sys.path`). La API pública (`from teaf import ...`, los símbolos de `__all__` de `teaf/__init__.py`) no cambia en absoluto — cero cambios requeridos en código consumidor. Ver [ADR-006](docs/architecture/adr/ADR-006-internal-namespace-refactor.md).
  - `pyproject.toml`: `[tool.setuptools.packages.find].include` ya no declara `backend*` — `teaf._internal` se descubre automáticamente como subpaquete de `teaf*`. Mismo ajuste en `[tool.ruff].src` y `[tool.mypy].packages`.
  - `scripts/check_public_api_boundary.py`: generalizado de coincidencia por raíz a coincidencia por **prefijo punteado**, necesario porque `teaf._internal` (a diferencia del antiguo `backend`) es un namespace de dos segmentos que cuelga del propio namespace público `teaf`. `PRIVATE_NAMESPACES` pasa de `("backend",)` a `("teaf._internal",)`. `check_paths()` gana un parámetro `forbidden` opcional.
  - **`scripts/check_internal_namespace.py`** (nuevo): verificador de integridad de la migración — confirma que no queda ningún import de `backend.*`, que `backend/` no existe en disco, y que todo el árbol `teaf.*` sigue siendo importable de punta a punta.
  - 4 pruebas nuevas (`tests/unit/test_internal_namespace.py`): ausencia de `backend` como paquete de nivel superior, `teaf._internal` importable, ningún import de `backend.*` en el repositorio, superficie pública intacta tras el refactor. Suite completa: 499 pruebas (495 + 4 nuevas).
  - Sin cambios funcionales: mismos módulos, mismas clases, mismo comportamiento — únicamente reorganización de namespace y reescritura mecánica de 402 líneas de import en 125 archivos.

## [0.6.1-alpha] - 2026-08-03

### Added

- **API Pública `teaf/`** (Sprint 2.5.1, Public SDK & Packaging): TEAF se instala como un paquete Python profesional (`pip install -e .`) y se consume exclusivamente vía `from teaf import ...` — sin conocer `backend/` por dentro. Sin capacidades nuevas del Runtime, sin módulos nuevos: exclusivamente empaquetado y experiencia de desarrollador sobre lo construido en los Sprints 2.1-2.6.
  - **Catorce símbolos principales** (`teaf/__init__.py`, `__all__` explícito): `Application`, `Runtime`, `Module` (alias de `ModuleBase`), `ModuleBase`, `ModuleBuilder`, `ModuleContext`, `ModuleManifest`, `ServiceContainer`, `EventBus`, `CapabilityRegistry`, `ModuleRegistry`, `Health` (alias de `CapabilityHealth`), `Configuration` (alias de `Settings`), `Version` — más cinco símbolos compañero imprescindibles para usarlos sin recurrir a `backend.*` (`Lifetime`, `Event`, `CapabilityCategory`, `ModuleCategory`, `get_configuration`).
  - **Nueve fachadas** bajo `teaf/` (`application.py`, `runtime.py`, `modules.py`, `services.py`, `events.py`, `configuration.py`, `capabilities.py`, `health.py`, `version.py`), cada una con su propio `__all__`, ninguna importa a otra — todas importan directamente de `backend/` (dirección de dependencias siempre `teaf/ → backend/`, nunca al revés, para evitar un ciclo real con `backend.core.application`).
  - **`Application`**: fachada de aplicación, callable ASGI (`Application()` se sirve directamente con `uvicorn app:app`), con `.runtime`, `.version`, `.asgi` (vía de escape al `FastAPI` subyacente).
  - **`teaf.version`**: único punto de verdad de cinco números de versión independientes — `FRAMEWORK_VERSION`, `SDK_VERSION`, `RUNTIME_VERSION` (nuevo — `backend/runtime/__init__.py`), `MODULE_SPEC_VERSION`, `PUBLIC_API_VERSION` (nuevo, nace en este Sprint) —, la clase `Version` (instancia ya construida, `teaf.Version`) y `is_compatible(actual, constraint)`, una utilidad de comparación de versiones independiente del ciclo de vida de un módulo.
  - **`scripts/check_public_api_boundary.py`**: verificador estático (basado en `ast`, nunca ejecuta el código analizado) de que un árbol de archivos solo importa `teaf`, nunca `backend.*` — sienta la base para una futura verificación en CI, sin estar cableado a ningún pipeline todavía.
  - **`examples/`** (3 ejemplos ejecutables, cada uno con su propio `README.md`): `hello-world/` (ciclo de vida mínimo), `basic-module/` (autoría de un módulo propio), `application-bootstrap/` (una `Application` completa con un módulo registrado) — los tres importan exclusivamente `from teaf import ...`, verificado por el checker de límites y por pruebas dedicadas.
  - **`docs/public-api/`** (5 documentos): `PUBLIC-API.md`, `PACKAGE-STRUCTURE.md`, `IMPORT-GUIDE.md`, `VERSIONING.md`, `MIGRATION-GUIDE.md`.
  - **`pyproject.toml`**: sección `[project]` completa (`name = "teaf"`, versión, clasificadores, `requires-python = ">=3.11"`, dependencias sincronizadas con `requirements.txt`), `[build-system]` (`setuptools`), descubrimiento de paquetes (`teaf*` + `backend*`), `teaf/py.typed` (PEP 561). Sin `[project.scripts]` — sin CLI todavía (ver "NO IMPLEMENTAR").
- 68 pruebas nuevas (494 en total): superficie pública completa (`__all__`, identidad de alias, sin fugas de `backend.*`), cada fachada por separado, un flujo completo de autoría de módulo usando solo `teaf.*` contra un `Runtime` real, el verificador de límites (unitarias + contra `examples/` real), ejecución real de los tres ejemplos como subprocesos, `Application` como ASGI real (`httpx.ASGITransport`), y metadata de empaquetado (`pyproject.toml` ⇄ `requirements.txt` ⇄ distribución instalada). Cobertura del código nuevo de Sprint 2.5.1: 100% (`teaf/`), 98% (`scripts/check_public_api_boundary.py`, solo sin cubrir el bloque `if __name__ == "__main__":`).

### Changed

- Versión del framework: `0.6.0-alpha` → `0.6.1-alpha`. Nota de numeración: este Sprint se planificó como "2.5.1" (una continuación directa de Sprint 2.5/v0.5.0-alpha), pero se implementó después de que Sprint 2.6 ya hubiera publicado v0.6.0-alpha — se usa v0.6.1-alpha (PATCH sobre la versión real vigente) en vez de v0.5.1-alpha para no retroceder el historial de versiones.
- `docs/architecture/MODULE-CATALOG.md`: sin cambios — este Sprint no introduce ni modifica ningún módulo del catálogo.

### Notes

- Sin capacidades nuevas del Runtime, sin módulos nuevos, sin cambios funcionales en `backend/runtime/` ni `backend/sdk/` (la única adición en esas rutas es la constante `RUNTIME_VERSION` en `backend/runtime/__init__.py`, puramente declarativa). `DatabaseModule` (Sprint 2.6) sigue sin cablearse en `create_app()` y sin exponerse desde `teaf/` — sigue siendo opt-in.
- Verificado: `pip install -e .` instala correctamente (`teaf==0.6.1a0` normalizado PEP 440); `import teaf` y cada `from teaf import ...` funcionan; sin dependencias circulares (`teaf/ → backend/` en un solo sentido); el Runtime y el arranque real (`uvicorn`) siguen funcionando sin cambios de comportamiento; los tres ejemplos de `examples/` corren de extremo a extremo importando solo `teaf`.

## [0.6.0-alpha] - 2026-08-03

### Added

- **Database Module** (Sprint 2.6, Enterprise Persistence Foundation): el primer módulo oficial de TEAF construido enteramente sobre el [Module SDK](docs/sdk/SDK.md) (Sprint 2.5) — sin una sola llamada directa a `ServiceContainer`/`CapabilityRegistry`, todo pasa por `ModuleBase.bootstrap()`.
  - **`backend/providers/database/`** (extiende el andamiaje de Sprint 2.2 con implementación real): `engine.py` (`DatabaseDialect` SQLite/PostgreSQL/SQL Server, `create_engine()` async sobre SQLAlchemy 2.x — SQLite con `StaticPool` para bases de datos en memoria), `base_model.py` (`Base` declarativa + `AuditMixin`: `id` UUID, `created_at`/`updated_at`/`deleted_at`), `sqlalchemy_session.py`/`sqlalchemy_provider.py`/`sqlalchemy_factory.py` (implementaciones reales de `DatabaseSession`/`ConnectionManager`/`DatabaseFactory`), `sqlalchemy_repository.py` (`SQLAlchemyRepository`: CRUD genérico, paginación, filtros de igualdad, soft delete — nunca `commit()`, solo `flush()`), `sqlalchemy_unit_of_work.py` (`SQLAlchemyUnitOfWork`/`Factory`: sin commit implícito, rollback automático en excepción).
  - **`backend/modules/database/`** (el módulo SDK): `configuration.py` (`DatabaseConfiguration`, con `from_mapping()`), `health.py` (`DatabaseHealth`: caché síncrona + `refresh()` asíncrono, resuelve el desajuste entre el `ModuleHealth.check` síncrono del SDK y `health_check()` asíncrono del proveedor), `installer.py` (`DatabaseInstaller`: orquesta Alembic vía su API programática, deliberadamente síncrono y nunca invocado desde los hooks async de `DatabaseModule`), `manifest.py` (`build_database_manifest`: 6 capacidades, 3 servicios, 6 claves de configuración, 1 healthcheck, 2 eventos), `module.py` (`DatabaseModule(ModuleBase)`: motor/proveedor/health construidos en `__init__`, antes de que `bootstrap()` llame a `get_manifest()` por primera vez).
  - **Alembic**: `alembic.ini` + `database/migrations/` (entorno async, plantilla, una revisión baseline sin tablas de negocio) — migraciones de infraestructura, sin lógica de negocio.
  - `DatabaseModule` no está cableado en `create_app()` — opt-in, igual que el resto del SDK en Sprint 2.5.
- 73 pruebas nuevas (415 en total): motor/dialectos, modelo base, sesión/proveedor/fábrica, repositorio (incluye la prueba central de que nunca hace `commit()`), Unit of Work (incluye la prueba central de que nunca hace commit implícito), configuración, health, installer (Alembic real sobre `tmp_path`), manifiesto, y una prueba de integración end-to-end que arranca `DatabaseModule` contra un `Runtime` real. Cobertura del código nuevo de Sprint 2.6: 100%.
- `docs/modules/database/` (4 documentos): `DATABASE.md`, `REPOSITORY.md`, `UNIT-OF-WORK.md`, `MIGRATIONS.md`.

### Changed

- Versión del framework: `0.5.0-alpha` → `0.6.0-alpha`.
- `docs/architecture/MODULE-CATALOG.md`: la fila "Database" pasa de `Documentado` a `Implementado` (primer módulo del catálogo con código ejecutable, ver nota introducida en Sprint 2.0) y enlaza a `docs/modules/database/DATABASE.md`.
- `requirements.txt`: se añaden `sqlalchemy[asyncio]==2.0.36`, `alembic==1.14.0`, `aiosqlite==0.20.0`, `asyncpg==0.30.0`.
- `pyproject.toml`: `extend-exclude` de `ruff` incorpora `database/migrations/versions` (revisiones autogeneradas por Alembic, no se ajustan a las reglas de lint del proyecto).

### Notes

- Sin entidades ni tablas de negocio, sin autenticación/autorización, sin Azure, sin IA, sin MCP, sin Scheduler, sin driver SQL Server real (`aioodbc` no instalado, solo la estructura del dialecto), sin Oracle.
- Verificado sin dependencias circulares; `backend/modules/database/` importa de `backend/providers/database/` en un solo sentido; `backend/runtime/`, `backend/sdk/` y `backend/core/application.py::create_app()` no se modificaron en este Sprint — el módulo consume exclusivamente capacidades ya existentes del SDK y del Runtime.

## [0.5.0-alpha] - 2026-08-03

### Added

- **Module SDK** (Sprint 2.5, Developer Platform): paquete nuevo `backend/sdk/`, dependiente de `backend/core/` y `backend/runtime/` (a diferencia de `backend/runtime/`, que nunca depende de `contracts/`/`providers/` — el SDK sí depende del Runtime: es la capa de autoría de alto nivel apoyada en él). Un desarrollador crea un módulo completo heredando únicamente de `ModuleBase`.
  - **Primitivas de descripción**: `ModuleDescriptor` (metadata de autoría, homónimo deliberado de `backend.core.registry.ModuleDescriptor`), `ModuleConfiguration`, `ModuleHealth` (reutiliza `CapabilityHealth`), `ModuleCapability`, `ModuleService`, `ModuleDependency`, `ModuleCategory` (7 valores).
  - **`ModuleManifest`**: compone `ModuleDescriptor` + license/capabilities/dependencies/configuration/services/health_checks/events/runtime_compatibility/sdk_compatibility, con `as_dict()` aplanado.
  - **`ModuleSpecification v1`** (`specification.py`): diez secciones formales (Metadata, Lifecycle, Dependencies, Capabilities, Configuration, Services, Health, Documentation, Packaging, Validation Rules).
  - **`ModuleBuilder`** (`builder.py`): builder fluido — `with_*`/`add_*`/`build()` — única forma probada de construir un `ModuleManifest`.
  - **`ModuleValidator`** (`validator.py`): valida metadata (slug/semver), duplicados (capacidades/servicios/configuración/health checks/dependencias), auto-dependencias y compatibilidad Runtime/SDK; `validate()`, `validate_or_raise()`, `errors_by_section()`.
  - **`ModuleDependencyResolver`** (`dependency_resolver.py`): resuelve orden de inicialización entre varios manifiestos, detecta ciclos (reutilizando `backend.runtime.dependency_graph.DependencyGraph` vía un adaptador estructural), detecta conflictos de versión, construye árboles de dependencias.
  - **`ServiceBinder`/`CapabilityBinder`** (`service_binder.py`, `capability_binder.py`): traducen `ModuleService`/`ModuleCapability` en registros reales contra `Runtime.register_service`/`register_capability` — el autor del módulo nunca llama al `ServiceContainer`/`CapabilityRegistry` directamente.
  - **`ModuleContext`** (`context.py`): envuelve un `Runtime` + configuración + logger con nombre; atajos `.container`, `.capabilities`, `.features`, `.events`.
  - **`ModuleBase`** (`module_base.py`): la única clase de la que hereda un módulo. Siete hooks opcionales, síncronos o asíncronos (`initialize`, `configure`, `register`, `start`, `ready`, `stop`, `dispose`); `bootstrap()`/`shutdown()` orquestan validación, comprobación de compatibilidad, registro en `ModuleRegistry`, enlace automático de servicios/capacidades y ejecución de hooks, avanzando `ModuleLifecycle` en cada paso.
  - **`ModuleLifecycle`/`ModuleLifecycleState`** (`lifecycle.py`): ocho estados (created → initialized → configured → registered → started → ready → stopped → disposed, más `failed` terminal alcanzable desde cualquier punto), con historial y protección contra retrocesos.
  - **`ModuleInspector`** (`inspector.py`): introspección de solo lectura — `describe`/`services`/`capabilities`/`dependencies`/`events`/`configuration`/`health`/`manifest`.
  - **`MODULE_TEMPLATES`/`ModuleScaffolder`** (`templates.py`, `scaffolder.py`): 7 plantillas (Generic, Database, Security, Storage, Integration, AI, MCP), sin código de negocio; `scaffold()` genera un esqueleto en memoria (Python válido), `write_to_disk()` lo materializa como paso explícito — sin CLI.
  - **`ModuleDocumentationGenerator`** (`documentation_generator.py`): genera Markdown a partir de un `ModuleManifest` — solo el servicio, sin escribir archivos.
  - **`ModuleCertification`** (`certification.py`): certifica ocho secciones (Specification, Manifest, Metadata, Capabilities, Dependencies, Version, Health, Documentation) — más estricta que `ModuleValidator` en `documentation` (requerida para certificar, no para registrarse).
  - Cinco excepciones nuevas: `ModuleValidationException`, `ModuleCompatibilityException`, `ModuleDependencyException`, `ModuleRegistrationException`, `ModuleLifecycleException`.
- 130 pruebas nuevas (342 en total): primitivas, manifiesto/especificación, builder, validador, resolutor de dependencias, binders, `ModuleBase`/`ModuleContext` (incluye todos los caminos de fallo y comparador de compatibilidad), inspector, plantillas/scaffolder, generador de documentación, certificación. Cobertura del código nuevo de Sprint 2.5: 100%.
- `docs/sdk/` (6 documentos): `SDK.md`, `MODULE-SPECIFICATION.md`, `MODULE-BUILDER.md`, `MODULE-LIFECYCLE.md`, `MODULE-CERTIFICATION.md`, `DEVELOPER-GUIDE.md`.

### Changed

- Versión del framework: `0.4.0-alpha` → `0.5.0-alpha`.

### Notes

- Sprint 2.5 es exclusivamente infraestructura de autoría: ningún módulo real (Database, Security, AI, ...) se implementa con el SDK todavía — sin CLI, sin generación de proyectos completos, sin persistencia de módulos, sin Database/Security/Storage/Scheduler/OpenTelemetry/Azure/MCP/AI reales.
- Verificado sin dependencias circulares; `backend/sdk/` depende de `backend/core/` y `backend/runtime/` en un solo sentido (ningún archivo de `runtime/`/`core/` importa `sdk/`); el arranque real (`uvicorn`) sigue sirviendo correctamente sin ningún módulo SDK cableado en `application.py` (el SDK es opt-in, no se auto-carga).

## [0.4.0-alpha] - 2026-08-03

### Added

- **Platform Intelligence** (Sprint 2.4): el Runtime gana la capacidad de describirse a sí mismo — extiende, no reemplaza, la infraestructura de Sprint 2.3.
  - **Capability Model** (`backend/runtime/capabilities/`): `CapabilityMetadata` (17 campos), `Capability`, `CapabilityCategory` (13 valores), `CapabilityStatus`, `CapabilityHealth`, `CapabilityBuilder` (fluido) y `CapabilityRegistry` (`register`/`unregister`/`find`/`exists`/`list`/`search`/`describe`). Ninguna capacidad real registrada.
  - `CapabilityProviderRegistry` (`provider_registry.py`): agregación de capacidades de múltiples proveedores vía un `typing.Protocol` estructural (`CapabilityProviderLike`), sin importar `backend/contracts/` — preparación para un futuro servidor MCP, sin implementarlo.
  - **Feature Flags** (`backend/runtime/features/`): `FeatureFlag`, `FeatureManager` (`register`/`enable`/`disable`/`exists`/`is_enabled`/`list`/`describe`), `FeatureGroup` (7 valores: Platform, Security, Database, AI, MCP, Experimental, Infrastructure), `FeatureStatus`. Sin persistencia.
  - `ModuleDescriptor` (`backend/core/registry.py`) gana campos aditivos: `author`, `description`, `lifecycle_state` (nuevo `ModuleLifecycleState`, propio de Core), `capabilities`, `tags`, `documentation`, `experimental`, `created_at`, `updated_at`, propiedad `id` y `as_dict()`; `ModuleRegistry` gana `unregister()`.
  - `Plugin` (`backend/runtime/plugin_loader.py`) gana la propiedad `metadata` (`PluginMetadata`, derivada por defecto de `name`/`version`); `PluginLoader` gana `unload()`.
  - `ServiceContainer` (`backend/runtime/container.py`) gana `ServiceMetadata`, `ServiceHealth`, registro opcional de metadata en `register_singleton`/`register_scoped`/`register_transient`/`register_instance`, `unregister()` y `describe_services()`.
  - `EventBus` (`backend/runtime/event_bus.py`) gana historial acotado (`history_limit`, `history(limit=...)`) — retiene los eventos publicados aunque no haya suscriptores.
  - `ServiceDiscovery` (`backend/runtime/service_discovery.py`): `list`/`search`/`resolve`/`describe`/`capabilities`/`dependency_tree` (con protección contra ciclos) sobre `ServiceContainer`.
  - `RuntimeDiagnostics` (`backend/runtime/diagnostics.py`) y `RuntimeSelfDescription` (`backend/runtime/self_description.py`): las dos fotografías extendidas del estado del Runtime, servidas por `Runtime.diagnostics()`/`Runtime.self_description()`.
  - `Runtime` (`backend/runtime/runtime.py`) gana: atributos compuestos `capability_registry`, `feature_manager`, `capability_provider_registry`, `service_discovery`, `framework_version`, `modules`; wrappers `register_module`/`unregister_module`, `register_service`/`remove_service`/`resolve_service`, `register_capability`/`remove_capability`, `load_plugin`/`unload_plugin`, `enable_feature`/`disable_feature` (cada uno publica su evento correspondiente en el `EventBus`); eventos nuevos `framework.started`/`framework.stopped` (junto a los ya existentes, por compatibilidad), `module.registered`/`module.unregistered`, `service.registered`/`service.removed`/`service.resolved`, `capability.registered`/`capability.removed`, `plugin.loaded`/`plugin.unloaded`, `feature.enabled`/`feature.disabled`.
  - **Runtime API** (`backend/runtime/api.py`, `GET /runtime/*`): `info`, `modules`, `services`, `plugins`, `capabilities`, `features`, `events` (con `?limit=`), `configuration`, `dependencies`, `self` — 10 endpoints, toda la información leída en vivo del Runtime.
  - **Developer API** (`backend/developer/runtime_api.py`, paquete nuevo): `DeveloperRuntimeAPI` — mismas 9 superficies de consulta que la Runtime API (salvo `self`), sin HTTP, reutilizando las funciones `build_*_payload` del router para no duplicar el ensamblado de datos.
  - **Runtime Manifest** (`backend/runtime/manifest.py`): `generate_manifest()`/`write_manifest()` producen `runtime.manifest.json` (Framework, Version, Runtime, Modules, Capabilities, Services, Plugins, Configuration, Feature Flags, Contracts, Providers, Factories) — generado automáticamente al arrancar (excepto en `TESTING`), gitignored.
  - Contratos nuevos en `backend/contracts/`: `CapabilityProvider` y `FrameworkKnowledgeProvider` — preparación para IA/MCP, sin implementación.
  - `backend/core/application.py`: monta `create_runtime_router`, construye `DeveloperRuntimeAPI`, genera `runtime.manifest.json` en `_lifespan` (guardado ante `OSError`), y expone `_configuration_summary()` como fuente única del resumen de configuración no sensible.
- 96 pruebas nuevas (212 en total): Capability Model, Feature Flags, Service Discovery, extensiones de `Runtime` (wrappers + eventos + `diagnostics()`/`self_description()`), Runtime Manifest, Developer API, Runtime API (integración HTTP) y extensiones de `ModuleDescriptor`/`PluginMetadata`/`ServiceMetadata`/`EventBus`. Cobertura del código nuevo de Sprint 2.4: 100%.
- `docs/platform/` (5 documentos): `PLATFORM-INTELLIGENCE.md`, `CAPABILITY-REGISTRY.md`, `RUNTIME-API.md`, `DEVELOPER-API.md`, `SELF-DESCRIBING-RUNTIME.md`.

### Changed

- Versión del framework: `0.3.0-alpha` → `0.4.0-alpha`.
- `.gitignore`: nueva entrada `runtime.manifest.json` (artefacto generado, nunca versionado).

### Notes

- Sprint 2.4 es exclusivamente infraestructura de introspección: ninguna capacidad, feature flag ni plugin real se registra — sin persistencia, sin IA, sin MCP, sin autenticación en la Runtime API todavía.
- Verificado sin dependencias circulares, `backend/runtime/` sigue sin importar `backend/contracts/` ni `backend/providers/` (incluida la nueva preparación para MCP, resuelta con `typing.Protocol` estructural), y el arranque real (`uvicorn`) sirve correctamente los 10 endpoints de `/runtime/*` además de `/info`.

## [0.3.0-alpha] - 2026-08-02

### Added

- **Framework Runtime** (Sprint 2.3): paquete `backend/runtime/`, independiente de `contracts/`/`providers/` (solo depende de `backend/core/`):
  - `ServiceContainer` (`container.py`): resolución por contrato con ciclos de vida Singleton/Scoped/Transient, resolución perezosa (`resolve_lazy`/`Lazy[T]`), factories que resuelven otras dependencias, y detección de dependencias circulares (`CircularDependencyException`).
  - `LifecycleManager` (`lifecycle.py`): cinco etapas (Bootstrap → Startup → Running → Shutdown → Stopped) con hooks síncronos o asíncronos por etapa.
  - `StartupPipeline`/`ShutdownPipeline` (`pipeline.py`): pasos nombrados, FIFO en el arranque y LIFO en el apagado.
  - `ModuleDiscovery` (`discovery.py`): lectura del `ModuleRegistry` con filtro opcional por estado.
  - `DependencyGraph` (`dependency_graph.py`): grafo de dependencias entre módulos con detección de ciclos y orden topológico, verificado antes de correr el `StartupPipeline`.
  - `EventBus` (`event_bus.py`): publicación/suscripción síncrona interna, sin mensajería distribuida.
  - `PluginLoader` (`plugin_loader.py`): contrato `Plugin` mínimo y mecanismo de carga/validación, sin plugins reales.
  - `ConfigurationPipeline` (`configuration_pipeline.py`): validadores de configuración por módulo, ejecutados antes de verificar el grafo de dependencias.
  - `Runtime` (`runtime.py`): orquestador que compone todo lo anterior; conectado al ciclo de vida de FastAPI vía `lifespan` en `backend/core/application.py`.
- `ModuleDescriptor` (`backend/core/registry.py`) gana el campo aditivo `dependencies: tuple[str, ...]` — el módulo `ai` ya declara `("security",)`, reflejando la regla ya fijada en FRAMEWORK-BLUEPRINT.md.
- `GET /info` ampliado con `state`, `lifecycleStage`, `loadedModules` y `registeredCapabilities` del Runtime, leídos en cada petición (no una fotografía capturada al arrancar).
- 60 pruebas nuevas (116 en total): Service Container, Lifecycle, Pipelines, Event Bus, Module Discovery, Dependency Graph, Plugin Loader, Configuration Pipeline y el `Runtime` orquestador — sin integraciones con servicios reales.
- `docs/runtime/RUNTIME.md` documenta la arquitectura del Runtime, el ciclo de vida, el registro de módulos, el contenedor de servicios, el event bus, el plugin loader y las buenas prácticas de extensión.

### Changed

- Versión del framework: `0.2.0-alpha` → `0.3.0-alpha`.
- `backend/core/application.py`: ahora usa `lifespan` de FastAPI para arrancar/apagar el `Runtime`; `/info` recibe un `Callable` que lee el estado del Runtime en vivo en vez del registro estático anterior.

### Notes

- Sprint 2.3 es exclusivamente infraestructura de ejecución: Service Container, ciclo de vida, pipelines, descubrimiento, grafo de dependencias, event bus y plugin loader — sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, scheduler, notificaciones ni storage reales, sin Docker ni Azure).
- Verificado sin dependencias circulares a nivel de archivo y que `backend/core/` (salvo `application.py`, el composition root ya documentado) sigue sin depender de ningún otro módulo del framework.

## [0.2.0-alpha] - 2026-08-02

### Added

- Estructura inicial del monorepo del framework: `backend/`, `frontend/`, `database/`, `docker/`, `scripts/`, `tests/`, `docs/`, `.github/`.
- Documentación base de arquitectura: `docs/architecture/ARCHITECTURE.md` y `docs/architecture/STACK.md`.
- Roadmap del framework con 5 versiones planificadas: `docs/roadmap/ROADMAP.md`.
- Primeros 5 Architecture Decision Records (ADR-001 a ADR-005) sobre FastAPI, PostgreSQL, Docker, API First y Cloud Ready.
- Estándares obligatorios del framework: API, base de datos, código, seguridad y logging (`docs/standards/`).
- Gobernanza de GitHub: `CODEOWNERS`, plantillas de Issues y Pull Request, `CONTRIBUTING.md`.
- Licencia MIT del proyecto.
- `CLAUDE.md`, `/templates/` (9 plantillas reutilizables), estándar de Git (`GIT-STANDARD.md`), backlog inicial (`BACKLOG.md`), catálogo de módulos (`MODULE-CATALOG.md`), quality gates, definition of done y glosario del proyecto.
- Framework Blueprint oficial (`docs/architecture/FRAMEWORK-BLUEPRINT.md`) con 12 diagramas Mermaid (arquitectura por capas, mapa de dependencias, flujos de inicialización/petición/excepción, arquitectura física de despliegue, arquitectura de seguridad, proveedores de IA y MCP) y documentos complementarios `NFR.md`, `DECISION-TREE.md`, `EXTENSIBILITY.md`.
- **Bootstrap ejecutable del framework** (Sprint 2.1): Application Factory (`backend/core/application.py`), configuración por entorno (Development/Testing/Staging/Production), logging estructurado (consola/JSON/archivo con rotación), jerarquía de excepciones (`ApplicationException` y 6 subtipos), middlewares de correlation-id y logging de peticiones, manejo centralizado de errores en formato RFC 7807, rutas de sistema (`/`, `/health`, `/live`, `/ready`), utilidades genéricas en `shared/`, y suite de pruebas base (`tests/unit/`, `tests/integration/`). Documentado en `docs/core/CORE.md`.
- Manifiestos de dependencias del backend (`requirements.txt`, `requirements-dev.txt`) y configuración de herramientas (`pyproject.toml`: ruff, black, mypy, pytest).
- **Infrastructure Foundation** (Sprint 2.2): paquete `backend/contracts/` con 9 interfaces puras (Repository, UnitOfWork, DatabaseProvider, Authentication/AuthorizationProvider, TelemetryProvider, StorageProvider, AIProvider, SchedulerProvider, NotificationProvider); paquete `backend/providers/` con clases base y factories abstractas para database (`DatabaseFactory`, `DatabaseSession`, `ConnectionManager`, `RepositoryBase`), security (`SecurityContext`, `AuthenticationManager`, `AuthorizationManager`, RBAC, `SecurityFactory`), telemetry (`TracerProvider`, `MetricsProvider`, `LoggerProvider`, `TelemetryContext`), storage y ai; `ModuleRegistry` (`backend/core/registry.py`) registrado por instancia de aplicación (no como singleton de proceso); expansión de la inyección de dependencias (`backend/providers/dependencies.py`); nueva ruta `/info` con versión y estado de los módulos registrados. Documentado en `docs/infrastructure/INFRASTRUCTURE.md`. 32 pruebas nuevas (contracts, registry, factories, DI) — sin integraciones reales.

### Changed

- `README.md`: la sección "Cómo iniciar el proyecto" ahora documenta pasos reales de arranque (`uvicorn backend.main:app --reload`), en vez de la nota de "sin código ejecutable" de la iteración de fundación.
- Versión del framework (`FRAMEWORK_VERSION` en `backend/core/application.py`, expuesta en `/health` y `/info`): `0.1.0` → `0.2.0-alpha`.

### Notes

- El backend ya es ejecutable end-to-end (`uvicorn backend.main:app --reload` responde en `/`, `/health`, `/live`, `/ready`, `/info`). Sigue sin haber base de datos, autenticación, frontend ejecutable, Docker ni CI/CD reales — llegan en Sprints posteriores (ver `docs/roadmap/ROADMAP.md`, Versión 1 en adelante).
- Sprint 2.2 es exclusivamente infraestructura abstracta: contratos y clases base, sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, storage ni scheduler reales).

[Unreleased]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.5.0-alpha...HEAD
[0.5.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.4.0-alpha...v0.5.0-alpha
[0.4.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.3.0-alpha...v0.4.0-alpha
[0.3.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.2.0-alpha...v0.3.0-alpha
[0.2.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/main...v0.2.0-alpha
