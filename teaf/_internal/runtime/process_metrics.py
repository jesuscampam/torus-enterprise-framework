"""Métricas de proceso (memoria residente, tiempo de CPU) por plataforma.

``Runtime.diagnostics()`` expone dos cifras auxiliares —memoria residente y
tiempo de CPU acumulado, vía ``GET /runtime/info``— que hasta este módulo se
obtenían con ``resource.getrusage()``: el módulo estándar de POSIX que **no
existe en Windows**. Como ``runtime.py`` lo importaba a nivel de módulo,
``from teaf import Application`` fallaba con ``ModuleNotFoundError`` en
cualquier máquina Windows, antes incluso de que la aplicación llegara a
arrancar (Windows Compatibility Patch, TEAF v0.10.1-alpha; unidades de
``ru_maxrss`` en macOS corregidas en v0.10.2-alpha).

Es diagnóstico auxiliar, no comportamiento funcional: ninguna decisión de
arranque, enrutamiento o ciclo de vida depende de estas dos cifras — de
hecho ``RuntimeDiagnostics.memory_rss_bytes``/``cpu_time_seconds``
(``diagnostics.py``) ya eran ``int | None``/``float | None`` desde que
dejaron de ser los literales ``"not-implemented"`` de antes de Sprint 2.8.
Por eso la solución correcta no es ocultar el ``ModuleNotFoundError`` con un
``try/except: pass`` que deje la funcionalidad rota en silencio, sino dar a
cada plataforma su propia implementación real, detrás de dos funciones que
el resto del Runtime consume sin saber cuál corre debajo::

    Runtime.diagnostics()
            |
            v
    process_metrics (este módulo)
            |
       +----+----+
       |         |
     POSIX    Windows
    resource   os.times() + ctypes/psapi

**CPU** sí tiene un análogo portátil en la librería estándar: ``os.times()``
está documentado como disponible en Unix *y* Windows, y en ambos devuelve el
mismo par (tiempo de usuario, tiempo de sistema) que ``resource.getrusage``.
La implementación Windows reutiliza esa función en vez de reimplementar
``GetProcessTimes`` a mano vía ``ctypes`` — menos código propio, y con la
fiabilidad de la librería estándar detrás.

**Memoria** no tiene ese análogo: en Windows se consulta
``GetProcessMemoryInfo`` (``psapi.dll``) vía ``ctypes`` — ya en la librería
estándar de Windows, sin dependencia nueva — y se lee ``WorkingSetSize``, el
equivalente práctico de RSS en esa plataforma.

**En Linux el camino POSIX es idéntico** al que tenía ``Runtime`` antes de
que existiera este módulo. En **macOS sí cambia, y a propósito**: la
implementación anterior multiplicaba ``ru_maxrss`` por 1024 sin mirar la
plataforma, pero en Darwin ese campo **ya viene en bytes**, así que
reportaba 1024 veces la memoria real. Ver ``_RU_MAXRSS_TO_BYTES`` más abajo
y docs/PLATFORM-COMPATIBILITY.md.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Any

if sys.platform != "win32":
    import resource


def current_memory_rss_bytes() -> int | None:
    """Memoria residente (RSS) del proceso actual, en bytes.

    ``None`` si la consulta al sistema operativo falla — es una cifra de
    diagnóstico opcional, nunca debe tumbar ``Runtime.diagnostics()``.
    """
    if sys.platform == "win32":
        return _windows_memory_rss_bytes()
    return _posix_memory_rss_bytes()


def current_cpu_time_seconds() -> float | None:
    """Tiempo de CPU acumulado (usuario + sistema) del proceso actual, en segundos."""
    if sys.platform == "win32":
        return _windows_cpu_time_seconds()
    return _posix_cpu_time_seconds()


# -- POSIX (Linux, macOS, *BSD) -------------------------------------------------------------

#: Factor para convertir ``ru_maxrss`` a bytes. **No es la misma unidad en
#: todos los POSIX**, y es la única diferencia real de semántica entre Linux y
#: macOS en este módulo:
#:
#:     Linux, FreeBSD  ->  KiB    (getrusage(2): "in kilobytes")
#:     macOS / Darwin  ->  bytes  (getrusage(2): "in bytes")
#:
#: Multiplicar por 1024 en Darwin reportaría **1024 veces** la memoria real.
#: No es una hipótesis: es el mismo reparto que hace mypy en
#: ``mypy/dmypy_server.py`` (``factor = 1`` en darwin, ``1024`` en el resto).
#:
#: Se resuelve una sola vez al importar, no en cada llamada: la plataforma no
#: cambia durante la vida del proceso.
_RU_MAXRSS_TO_BYTES = 1 if sys.platform == "darwin" else 1024


def _posix_memory_rss_bytes() -> int:
    """Pico de memoria residente, normalizado a bytes en todos los POSIX."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * _RU_MAXRSS_TO_BYTES


def _posix_cpu_time_seconds() -> float:
    """``ru_utime``/``ru_stime`` son segundos en coma flotante en todo POSIX —
    aquí no hay divergencia de unidades que normalizar."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


# -- Windows ---------------------------------------------------------------------------------
# ``ctypes``/``ctypes.wintypes`` se importan siempre (son módulos puros de Python,
# sin llamadas al sistema operativo al importarse) para que este archivo sea
# importable — y comprobable con mypy — en cualquier plataforma. Lo que sí es
# exclusivo de Windows es el atributo ``ctypes.windll``, así que toda la
# configuración que lo usa queda dentro de este ``if``.


class _ProcessMemoryCounters(ctypes.Structure):
    """``PROCESS_MEMORY_COUNTERS`` completa (``psapi.h``).

    ``GetProcessMemoryInfo`` escribe la estructura entera de vuelta: declarar
    solo los primeros campos corrompería memoria, porque Windows escribiría
    más allá del buffer que ``ctypes`` reservó para una estructura truncada.
    Solo se lee ``WorkingSetSize`` más abajo, pero la estructura se declara
    completa por esa razón.
    """

    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


#: ``Any``, no un tipo de ``ctypes.WinDLL``: mypy poda la rama
#: ``if sys.platform == "win32":`` en cualquier máquina que no reporte esa
#: plataforma (aquí, Linux), así que necesitan un valor por defecto visible
#: para el chequeo estático fuera de esa rama. En tiempo de ejecución nunca
#: valen ``None`` cuando se usan: ``_windows_memory_rss_bytes`` /
#: ``_windows_cpu_time_seconds`` solo se llaman bajo el mismo
#: ``sys.platform == "win32"`` que los asigna.
_kernel32: Any = None
_psapi: Any = None

if sys.platform == "win32":
    _kernel32 = ctypes.windll.kernel32
    _psapi = ctypes.windll.psapi

    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    _psapi.GetProcessMemoryInfo.restype = wintypes.BOOL


def _windows_memory_rss_bytes() -> int | None:
    """``WorkingSetSize`` vía ``GetProcessMemoryInfo`` — el análogo práctico
    de RSS en Windows. No hay ningún caso conocido en que la llamada falle
    consultando el propio proceso, pero devolver ``None`` ante un fallo
    inesperado es más seguro que dejar propagar una excepción desde una
    cifra de diagnóstico opcional.

    **No hay fuga de recursos**: ``GetCurrentProcess()`` devuelve un
    *pseudo-handle* (constante ``-1``), no un handle real del kernel. No se
    abre nada, así que no hay nada que cerrar — llamar a ``CloseHandle``
    sobre él sería incorrecto. La estructura la gestiona ``ctypes`` y se
    libera con el ámbito.
    """
    try:
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        handle = _kernel32.GetCurrentProcess()
        if not _psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return None
        return int(counters.WorkingSetSize)
    except (AttributeError, OSError):
        return None


def _windows_cpu_time_seconds() -> float | None:
    try:
        times = os.times()
        return times.user + times.system
    except OSError:
        return None
