# Compatibilidad de plataforma — Linux, macOS, Windows

Qué sistema operativo necesita TEAF para importar, arrancar y servir una aplicación, y qué
diferencia hay entre ellos. Nace del Windows Compatibility Patch (v0.10.1-alpha) — hasta ese
parche, `from teaf import Application` **no funcionaba en Windows**.

## Estado por plataforma

| Plataforma | Import (`from teaf import Application`) | Arranque (`Runtime`) | HTTP (`/`, `/health`, `/info`, `/runtime/info`) |
|---|---|---|---|
| **Linux** | ✅ Verificado — es donde corre toda la suite de TEAF | ✅ Verificado | ✅ Verificado |
| **macOS** | ✅ Compatible por diseño (POSIX, mismo camino que Linux) — no verificado en este Sprint | ✅ Compatible por diseño | ✅ Compatible por diseño |
| **Windows** | ✅ Compatible por diseño — **no verificado en un Windows real** (ver «Qué significa cada estado» abajo) | ✅ Compatible por diseño | ✅ Compatible por diseño |

### Qué significa cada estado

- **Verificado**: se ejecutó de verdad en esa plataforma y se observó el resultado.
- **Compatible por diseño, no verificado**: el código no contiene ninguna API exclusiva de esa
  plataforma que se sepa (auditoría completa más abajo), y la parte que sí difiere por plataforma
  (`process_metrics.py`) se probó de forma estructural — simulando la superficie de Windows dentro
  de un intérprete Linux — pero **no contra un Windows real**. No hay una máquina Windows en el
  entorno donde se desarrolló este parche.

No se declara "Windows soportado" sin matices por esta misma razón: hacerlo sin haber ejecutado
`pip install -e .` y `from teaf import Application` en un Windows real sería exactamente el tipo de
afirmación no verificada que este documento existe para no hacer. **Validación pendiente**, primer
paso de quien tenga acceso a una máquina Windows:

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

| Cifra | POSIX | Windows |
|---|---|---|
| Tiempo de CPU | `resource.getrusage(RUSAGE_SELF)` — **sin cambios** respecto a antes del parche | `os.times()` — documentada por la librería estándar como disponible en Unix **y** Windows, devuelve el mismo par (usuario, sistema) |
| Memoria residente | `resource.getrusage(RUSAGE_SELF).ru_maxrss * 1024` — **sin cambios** | `GetProcessMemoryInfo` (`psapi.dll`) vía `ctypes`, leyendo `WorkingSetSize` — el análogo práctico de RSS en Windows |

Dos decisiones que merece la pena explicar:

- **El tiempo de CPU en Windows no usa `ctypes` en absoluto.** `os.times()` ya está en la librería
  estándar y ya funciona en ambas plataformas, así que reimplementar `GetProcessTimes` a mano
  habría sido más código propio para llegar exactamente al mismo resultado, con más superficie para
  un error.
- **La memoria sí necesita `ctypes`**, porque no hay un análogo portátil en la librería estándar.
  Sin dependencia nueva: `ctypes` y `ctypes.wintypes` son parte de Python. El único atributo
  exclusivo de Windows (`ctypes.windll`) queda aislado dentro de un `if sys.platform == "win32":`,
  para que el archivo se pueda importar —y comprobar con `mypy --strict`— en cualquier plataforma.

**El camino POSIX no cambió una sola línea** respecto a lo que hacía `Runtime` antes de que
existiera este módulo. Ninguna aplicación en Linux o macOS ve una diferencia de comportamiento.

## Otras dependencias exclusivas de una plataforma — auditoría

Además de `resource`, se buscó en todo el repositorio: `fcntl`, `pwd`, `grp`, `termios`, `tty`,
`pty`, `signal` (con señales específicas de POSIX), `os.uname`, `os.fork`, `os.getuid`,
`os.getgid`, y rutas fijas de tipo `/etc/`.

**Resultado: ninguna**, ni dentro de `teaf/` ni en el resto del repositorio (`scripts/`,
`benchmarks/`, `database/migrations/`).

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
