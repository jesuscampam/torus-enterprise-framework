# Compatibilidad de plataforma — Linux, macOS, Windows

Qué sistema operativo necesita TEAF para importar, arrancar y servir una aplicación, y qué
diferencia hay entre ellos. Nace del Windows Compatibility Patch (v0.10.1-alpha) — hasta ese
parche, `from teaf import Application` **no funcionaba en Windows**.

La otra mitad de "plataforma" es el intérprete: qué versiones de Python soporta TEAF, y cuáles se
ejecutaron de verdad, está en [Versiones de Python](#versiones-de-python) más abajo.

## Estado por plataforma

| Plataforma | Import (`from teaf import Application`) | Arranque (`Runtime`) | HTTP (`/`, `/health`, `/info`, `/runtime/info`) | Métricas de proceso |
|---|---|---|---|---|
| **Linux** | ✅ Verificado — es donde corre toda la suite de TEAF | ✅ Verificado | ✅ Verificado | ✅ Verificado (contrastado contra `/proc/self/status`) |
| **macOS** | ✅ Compatible por diseño (POSIX, mismo camino que Linux) | ✅ Compatible por diseño | ✅ Compatible por diseño | ⚠️ Compatible por diseño — unidad de `ru_maxrss` corregida, **no ejecutado en un Mac real** |
| **Windows** | ✅ Compatible por diseño | ✅ Compatible por diseño | ✅ Compatible por diseño | ⚠️ Compatible por diseño — `ctypes`/`psapi` probado solo contra un doble, **no en un Windows real** |

### Qué significa cada estado

- **Verificado**: se ejecutó de verdad en esa plataforma y se observó el resultado.
- **Compatible por diseño, no verificado**: el código no contiene ninguna API exclusiva de otra
  plataforma que se sepa (auditoría completa más abajo), y la parte que sí difiere
  (`process_metrics.py`) se probó **simulando** esa plataforma dentro de un intérprete Linux —
  `sys.platform` sustituido, y en el caso de Windows también `ctypes.windll` y un `resource`
  deliberadamente inutilizable. Es verificación de la mecánica, no de la plataforma: en el entorno
  donde se desarrolló esto **no hay ni una máquina Windows ni un Mac**.

  Lo que esto sí descarta con certeza: que el import falle, que el despacho elija el backend
  equivocado, o que la estructura `ctypes` esté mal montada. Lo que **no** puede descartar: que la
  API real del sistema devuelva algo distinto de lo que devuelve el doble.

No se declara "Windows soportado" sin matices por esta misma razón: hacerlo sin haber ejecutado
`pip install -e .` y `from teaf import Application` en un Windows real sería exactamente el tipo de
afirmación no verificada que este documento existe para no hacer. **Validación pendiente**, primer
paso de quien tenga acceso a una máquina Windows (en un Mac, el equivalente con `python3`):

```powershell
python --version
pip install -e .
python -c "from teaf import Application; print(Application)"
uvicorn app:app          # con una app mínima, ver examples/hello-world/
# y, en otra terminal:
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/runtime/info
```

## Causa raíz del problema que corrige este parche

`teaf/_internal/runtime/runtime.py` importaba `resource` —módulo de la librería estándar
**exclusivo de POSIX**, sin equivalente en Windows— a nivel de módulo. Como `Runtime` está en la
cadena de import de `from teaf import Application` (vía `teaf.api` → `ApiProtectionModule` →
`ModuleContext` → `Runtime`), cualquier intento de importar TEAF en Windows fallaba con:

```
ModuleNotFoundError: No module named 'resource'
```

antes de que la aplicación que lo consume llegara a ejecutar una sola línea propia.

## Qué usaba `resource`, y por qué no era necesario perderlo

Dos cifras de diagnóstico, expuestas por `Runtime.diagnostics()` vía `GET /runtime/info`: memoria
residente (`memory_rss_bytes`) y tiempo de CPU acumulado (`cpu_time_seconds`). Ninguna decisión de
arranque, enrutamiento o ciclo de vida depende de ellas — son observabilidad, no comportamiento
funcional. De hecho ya eran opcionales en el modelo de datos (`int | None`/`float | None`) desde
que dejaron de ser los literales `"not-implemented"` de antes de Sprint 2.8.

Eso descartó la solución fácil y equivocada —`try: import resource / except ImportError: pass`,
dejando la funcionalidad rota en silencio en Windows— a favor de una real: cada plataforma obtiene
sus propias cifras, de verdad.

## La abstracción: `teaf._internal.runtime.process_metrics`

```
Runtime.diagnostics()
        |
        v
process_metrics.py
        |
   +----+----+
   |         |
 POSIX    Windows
resource   os.times() + ctypes/psapi
```

| Métrica | Linux | macOS | Windows |
|---|---|---|---|
| Memoria residente | `resource.getrusage(RUSAGE_SELF).ru_maxrss` × **1024** (viene en KiB) | `resource.getrusage(RUSAGE_SELF).ru_maxrss` × **1** (ya viene en bytes) | `GetProcessMemoryInfo` (`psapi.dll`) vía `ctypes` → `WorkingSetSize` |
| Tiempo de CPU | `resource.getrusage(RUSAGE_SELF)` → `ru_utime + ru_stime` | igual que Linux | `os.times()` → `user + system` |

Dos decisiones que merece la pena explicar:

- **El tiempo de CPU en Windows no usa `ctypes` en absoluto.** `os.times()` ya está en la librería
  estándar y ya funciona en ambas plataformas, así que reimplementar `GetProcessTimes` a mano
  habría sido más código propio para llegar exactamente al mismo resultado, con más superficie para
  un error.
- **La memoria sí necesita `ctypes`**, porque no hay un análogo portátil en la librería estándar.
  Sin dependencia nueva: `ctypes` y `ctypes.wintypes` son parte de Python. El único atributo
  exclusivo de Windows (`ctypes.windll`) queda aislado dentro de un `if sys.platform == "win32":`,
  para que el archivo se pueda importar —y comprobar con `mypy --strict`— en cualquier plataforma.

**En Linux el camino POSIX es idéntico** al de antes: mismo valor, mismo código, misma ruta de
ejecución. En macOS **sí cambia, y a propósito** — ver la sección siguiente.

## `ru_maxrss` no usa la misma unidad en todos los POSIX

Es la única diferencia real de semántica entre Linux y macOS en este módulo, y merece su propia
sección porque es silenciosa: no falla, simplemente devuelve un número equivocado.

| Sistema | Unidad de `ru_maxrss` | Fuente |
|---|---|---|
| Linux | KiB | `getrusage(2)`: *"maximum resident set size used (in kilobytes)"* |
| FreeBSD | KiB | `getrusage(2)`: *"in kilobytes"* |
| macOS / Darwin | **bytes** | `getrusage(2)`: *"the maximum resident set size utilized (in bytes)"* |

La primera versión de este módulo (v0.10.1-alpha, antes de esta corrección) multiplicaba por 1024
sin mirar la plataforma. En Linux era correcto; **en macOS reportaba 1024 veces la memoria real** —
del orden de gigabytes donde había megabytes.

Corregido con `_RU_MAXRSS_TO_BYTES`, un factor que se resuelve una sola vez al importar. Es el
mismo reparto que hace **mypy** en `mypy/dmypy_server.py` (`factor = 1` en `darwin`, `1024` en el
resto), lo que sirve de corroboración independiente de que la divergencia es real y de cuál es el
lado correcto.

> **Cambio de comportamiento en macOS, declarado.** Es la única desviación de la regla "no cambiar
> el comportamiento existente de Linux/macOS" de este sprint. Se corrige porque el valor anterior
> era sencillamente incorrecto, no una convención distinta: `memory_rss_bytes` promete bytes y en
> macOS no los devolvía. Linux no se ve afectado.

Cubierto por pruebas: el factor se comprueba para `linux`, `freebsd` y `darwin` simulados, y en
Linux se contrasta además contra `VmHWM` de `/proc/self/status`, que es el mismo pico de RSS en una
unidad sin ambigüedad.

## Otras dependencias exclusivas de una plataforma — auditoría

Además de `resource`, se buscó en todo el repositorio: `fcntl`, `pwd`, `grp`, `termios`, `tty`,
`pty`, `signal` (con señales específicas de POSIX), `os.uname`, `os.fork`, `os.getuid`,
`os.getgid`, y rutas fijas de tipo `/etc/`.

Resultado, clasificando cada hallazgo de **código propio** (se excluye `.venv/`: alembic, click,
pip y setuptools usan `fcntl`/`termios`/`pwd` bajo sus propias guardas y funcionan en Windows):

| Archivo | Línea | API | ¿En la cadena de import pública? | Acción |
|---|---|---|---|---|
| `teaf/_internal/runtime/process_metrics.py` | 61 | `import resource` | Sí | ✅ **Guardado** por `if sys.platform != "win32":` — es el arreglo |
| `tests/unit/test_process_metrics_platform.py` | 122 | `import resource` | No (suite de pruebas) | ✅ Dentro de una función de test; solo se ejecuta en POSIX |
| `loadtests/harness.py` | 27 | `import resource` | **No** | ⚠️ Sin guarda, pero fuera de alcance — ver abajo |

Ninguna otra: cero `fcntl`, `pwd`, `grp`, `termios`, `tty`, `pty`, `os.uname`, `os.fork`,
`os.getuid`, `os.getgid` o rutas `/etc/` en código propio.

Que `loadtests/harness.py` está fuera de la cadena pública **está comprobado, no supuesto**:
importar `teaf` en un intérprete limpio y mirar `sys.modules` no trae ningún módulo `loadtests`.

Dos coincidencias de la búsqueda inicial de "resource" resultaron ser falsos positivos, no
relacionados con el módulo estándar:

- `teaf._internal.modules.observability.module`: usa `opentelemetry.sdk.resources.Resource`, la
  clase de OpenTelemetry — nombre compartido, sin relación con `resource` de POSIX.
- `teaf._internal.contracts.security.AuthorizationManager.authorize`: `resource: str` es el nombre
  de un parámetro (el recurso sobre el que se autoriza en RBAC), no un import.

## Fuera del alcance de este parche — documentado, no corregido

`loadtests/harness.py` (herramienta de desarrollo, **no** parte del paquete `teaf` que se
distribuye) también importa `resource`, para medir memoria/CPU durante las pruebas de carga. No
bloquea `from teaf import Application` — las pruebas de carga no forman parte de la cadena de
import de la aplicación — así que queda fuera del alcance de este parche por su propia regla:
*"si aparece un problema que no bloquea el arranque en Windows, documentarlo como backlog y no
implementarlo en este patch"*. Corregirlo sería una repetición mecánica del mismo patrón que este
documento ya describe, sin ningún hallazgo nuevo que justifique tocar una herramienta de desarrollo
fuera de alcance.

## Limitaciones — las métricas no son perfectamente equivalentes entre plataformas

Las APIs subyacentes no son la misma cosa, así que **no se afirma equivalencia exacta**. Lo que sí
es equivalente es el *propósito*: una cifra de diagnóstico comparable consigo misma a lo largo del
tiempo, dentro de la misma plataforma.

| Diferencia | Detalle |
|---|---|
| **Pico vs. instantánea (memoria)** | En POSIX, `ru_maxrss` es el **máximo histórico** de RSS del proceso — nunca baja. En Windows, `WorkingSetSize` es el valor **actual** — sube y baja. Comparar la memoria de un proceso Linux con la de uno Windows no es una comparación entre iguales; el equivalente exacto de `ru_maxrss` en Windows sería `PeakWorkingSetSize`, que **no** se usa aquí para no cambiar el significado del campo respecto a la implementación original. |
| **Working Set ≠ RSS** | `WorkingSetSize` cuenta las páginas del proceso residentes en RAM, incluidas las compartidas; la contabilidad de páginas compartidas difiere de la de Linux. Es el análogo práctico, no idéntico. |
| **Resolución del tiempo de CPU** | `getrusage` reporta con resolución de microsegundos; `GetProcessTimes` —lo que hay debajo de `os.times()` en Windows— tiene una granularidad típica de ~15,6 ms. Para tiempos de CPU cortos, Windows es apreciablemente menos preciso. |
| **`ru_maxrss` en macOS** | Unidad distinta a la de Linux; normalizada — ver la sección anterior. |

Ninguna de estas diferencias afecta al arranque, al enrutamiento ni al ciclo de vida: las dos
cifras son observabilidad y ya eran `int | None`/`float | None`.

## Versiones de Python

"Plataforma" no es solo el sistema operativo: la versión del intérprete decide igual de rápido si
`pip install` funciona. Desde v0.10.3-alpha (Sprint 3.0.3), TEAF declara y soporta cuatro:

| Versión | Estado | Cómo se comprobó |
|---|---|---|
| **3.11** | ✅ Verificado | Intérprete por defecto del entorno de desarrollo. **1.272 pruebas en verde** |
| **3.12** | ⚠️ Compatible por diseño | Declarada en los clasificadores; **no ejecutada** — no hay 3.12 en este entorno. Está entre dos versiones verificadas |
| **3.13** | ✅ Verificado | CPython 3.13.12. Instalación limpia + **1.272 pruebas en verde** |
| **3.14** | ✅ Verificado | CPython **3.14.0rc2** (vía `uv`). Instalación limpia + **1.272 pruebas en verde**, resultados idénticos a 3.11 y 3.13 |

Los mismos dos estados que el resto de este documento: **Verificado** es "se ejecutó de verdad y se
observó el resultado"; **Compatible por diseño** es "nada indica que falle, pero nadie lo corrió".

`requires-python` sigue en **`>=3.11`**: ganar 3.14 no cuesta 3.11 ni 3.12. Lo que se comprueba
automáticamente es que la metadata no mienta —que `requires-python` y los clasificadores coincidan,
sin huecos, y que el intérprete en curso caiga dentro del rango declarado—, en
[`tests/unit/test_python_version_support.py`](../tests/unit/test_python_version_support.py) y
[`tests/unit/test_packaging_metadata.py`](../tests/unit/test_packaging_metadata.py).

En 3.14 se ejercitaron además los mismos criterios que en Linux: `from teaf import Application`,
`Version.as_dict()` (con `publicApi: 2.0.0`), el ciclo `bootstrapping → running → stopped` del
`Runtime`, y `GET /`, `/health`, `/info` y `/runtime/info` respondiendo 200 — este último con
`memoryRssBytes` y `cpuTimeSeconds` reales, no nulos, por el camino POSIX de `process_metrics.py`.

**El código de TEAF no necesitó ni un cambio.** Se auditó el árbol completo en busca de APIs
retiradas en 3.13/3.14 (`datetime.utcnow`, `distutils`, `asyncio.get_event_loop` sin bucle activo,
`imp`, `pkgutil.find_loader`): ninguna aparece. El bloqueo estaba íntegramente en tres dependencias
fijadas a versiones sin soporte para 3.14 — el detalle, en
[DEPENDENCIES.md](DEPENDENCIES.md#sprint-303--compatibilidad-con-python-314).

**Sin verificar en 3.14 en otro sistema operativo.** Todo lo anterior se ejecutó en Linux. La
combinación *Windows o macOS × Python 3.14* hereda las mismas reservas que la tabla del principio
de este documento: ninguna de las dos plataformas se ha ejecutado de verdad.

## Qué no cambió

- **API pública**: `from teaf import Application`, `from teaf import Version` y el resto de
  símbolos de `teaf.*` son idénticos. `PUBLIC_API_VERSION` no sube — `Runtime._current_memory_rss_bytes`/
  `_current_cpu_time_seconds` son métodos privados (con `_`), fuera de la superficie pública.
- **Comportamiento en Linux/Unix**: mismo valor, mismo código, misma ruta de ejecución.
- **`teaf-reference-app`**: no se ha modificado. El objetivo de este parche es que no necesite
  modificarse para funcionar en Windows.

## Referencias

- [`teaf/_internal/runtime/process_metrics.py`](../teaf/_internal/runtime/process_metrics.py) —
  la abstracción
- [`tests/unit/test_process_metrics_platform.py`](../tests/unit/test_process_metrics_platform.py)
  — regresión del import guardado, camino POSIX, simulación estructural de Windows
- [`tests/integration/test_windows_compatibility.py`](../tests/integration/test_windows_compatibility.py)
  — import, `Application`, ciclo de vida del `Runtime`, endpoints de sistema
- [DEPENDENCIES.md](DEPENDENCIES.md) — política de dependencias por plataforma
