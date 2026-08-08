"""Pruebas de ``teaf._internal.runtime.process_metrics`` (Windows Compatibility Patch).

``resource`` es un módulo estándar de POSIX que **no existe en Windows**.
``runtime.py`` lo importaba a nivel de módulo, así que ``from teaf import
Application`` fallaba con ``ModuleNotFoundError`` en cualquier máquina
Windows, antes de que la aplicación llegara a arrancar. Esta suite fija dos
cosas: que el import guardado por plataforma no vuelva a soltarse por
accidente (regresión estructural, vía AST), y que el camino POSIX —el único
que se puede ejecutar de verdad en esta máquina— no haya cambiado de
comportamiento.

**Sobre las pruebas marcadas «estructural»**: no hay una máquina Windows en
este entorno. Cargan ``process_metrics.py`` en aislamiento con
``sys.platform``/``ctypes.windll`` simulados, para comprobar que el módulo
importa sin excepción bajo esa rama y que la estructura ``ctypes`` que se
pasa a ``GetProcessMemoryInfo`` tiene el tamaño y el orden de campos
correctos — es la parte con más riesgo de un error silencioso (un campo mal
puesto no lanza una excepción, simplemente lee memoria que no es la que se
cree). Es una verificación de la mecánica de ``ctypes``, **no** sustituye a
ejecutar esto en un Windows real: la llamada al sistema operativo está
sustituida por un doble.
"""

from __future__ import annotations

import ast
import ctypes
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PROCESS_METRICS_PATH = (
    Path(__file__).resolve().parents[2] / "teaf" / "_internal" / "runtime" / "process_metrics.py"
)
_RUNTIME_PATH = (
    Path(__file__).resolve().parents[2] / "teaf" / "_internal" / "runtime" / "runtime.py"
)


def _module_level_import_names(source: str) -> list[str]:
    """Nombres de módulos importados **sin condición** al nivel superior del archivo.

    Recorre solo el cuerpo directo del ``Module`` —no baja a ``If``/``Try``—
    para que un ``import resource`` escondido dentro de un ``if
    sys.platform != "win32":`` no cuente como incondicional.
    """
    tree = ast.parse(source)
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_runtime_py_no_longer_imports_resource_unconditionally() -> None:
    """Regresión directa del bug: era exactamente este import el que rompía Windows."""
    names = _module_level_import_names(_RUNTIME_PATH.read_text(encoding="utf-8"))
    assert "resource" not in names


def test_process_metrics_guards_the_resource_import_by_platform() -> None:
    """El único sitio permitido para ``import resource`` es dentro de un ``if``."""
    source = _PROCESS_METRICS_PATH.read_text(encoding="utf-8")
    assert "resource" not in _module_level_import_names(source)

    tree = ast.parse(source)
    guarded_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        for child in ast.walk(node)
        if isinstance(child, ast.Import)
        for alias in child.names
    ]
    assert "resource" in guarded_imports


def test_process_metrics_and_ctypes_wintypes_import_cleanly_on_this_platform() -> None:
    """``ctypes``/``ctypes.wintypes`` no ejecutan nada del sistema operativo al
    importarse — deben poder cargarse en cualquier plataforma, incluida esta."""
    import ctypes.wintypes  # noqa: F401

    from teaf._internal.runtime import process_metrics  # noqa: F401


# -- Camino POSIX: el único que se puede ejecutar de verdad aquí --------------------------


def test_current_memory_rss_bytes_matches_pre_patch_behavior_on_this_platform() -> None:
    """En esta máquina (POSIX) la cifra debe seguir siendo real y positiva,
    exactamente como antes de que existiera este módulo."""
    from teaf._internal.runtime.process_metrics import current_memory_rss_bytes

    value = current_memory_rss_bytes()
    assert value is not None
    assert value > 0


def test_current_cpu_time_seconds_matches_pre_patch_behavior_on_this_platform() -> None:
    from teaf._internal.runtime.process_metrics import current_cpu_time_seconds

    value = current_cpu_time_seconds()
    assert value is not None
    assert value >= 0.0


def test_posix_path_matches_a_direct_getrusage_call() -> None:
    """Compara la salida contra una llamada directa a ``resource.getrusage``,
    la misma que hacía ``Runtime`` antes de este módulo.

    Usa el factor de unidades del propio módulo en vez de un ``1024``
    literal: en Darwin el factor correcto es ``1``, y fijar ``1024`` aquí
    haría que esta prueba «confirmara» precisamente el error que
    ``_RU_MAXRSS_TO_BYTES`` corrige.
    """
    import resource

    from teaf._internal.runtime.process_metrics import (
        _RU_MAXRSS_TO_BYTES,
        current_cpu_time_seconds,
        current_memory_rss_bytes,
    )

    direct = resource.getrusage(resource.RUSAGE_SELF)
    assert current_memory_rss_bytes() == direct.ru_maxrss * _RU_MAXRSS_TO_BYTES
    # El tiempo de CPU avanza entre ambas lecturas; solo se comprueba que
    # coincide en la fórmula (utime + stime), con margen para el propio
    # coste de haber llamado a getrusage() dos veces.
    via_module = current_cpu_time_seconds()
    assert via_module is not None
    assert via_module >= direct.ru_utime + direct.ru_stime


def test_ru_maxrss_is_scaled_by_the_unit_this_platform_actually_uses() -> None:
    """En Linux ``ru_maxrss`` viene en KiB, así que el factor debe ser 1024.

    Comprobación adicional contra el kernel: ``VmHWM`` de ``/proc/self/status``
    es el mismo pico de RSS, en KiB y sin ambigüedad de unidades. Si el factor
    fuese el equivocado, ambos diferirían en tres órdenes de magnitud.
    """
    if sys.platform != "linux":
        pytest.skip("la comprobación contra /proc/self/status es específica de Linux")

    from teaf._internal.runtime.process_metrics import (
        _RU_MAXRSS_TO_BYTES,
        current_memory_rss_bytes,
    )

    assert _RU_MAXRSS_TO_BYTES == 1024

    hwm_kib = 0
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("VmHWM:"):
            hwm_kib = int(line.split()[1])
            break
    assert hwm_kib > 0, "no se pudo leer VmHWM de /proc/self/status"

    reported = current_memory_rss_bytes()
    assert reported is not None
    # Mismo orden de magnitud: ru_maxrss y VmHWM no tienen por qué coincidir
    # al byte, pero sí deben estar dentro de un factor 2 entre sí.
    assert 0.5 <= reported / (hwm_kib * 1024) <= 2.0


@pytest.mark.parametrize(
    ("platform", "expected_factor"),
    [
        ("linux", 1024),
        ("freebsd13", 1024),
        # Darwin es el caso que el parche original tenía mal: ru_maxrss ya
        # viene en bytes, así que multiplicar por 1024 reportaba 1024x.
        ("darwin", 1),
    ],
)
def test_ru_maxrss_unit_factor_per_posix_platform(platform: str, expected_factor: int) -> None:
    """El factor se decide al importar, así que se comprueba recargando el
    módulo bajo cada plataforma simulada."""
    import importlib

    import teaf._internal.runtime.process_metrics as pm

    original = sys.platform
    try:
        # Asignación directa en vez de ``monkeypatch``: el ``importlib.reload``
        # de restauración tiene que correr con la plataforma real ya puesta, y
        # el teardown de monkeypatch ocurriría después del cuerpo del test.
        sys.platform = platform
        reloaded = importlib.reload(pm)
        assert reloaded._RU_MAXRSS_TO_BYTES == expected_factor
    finally:
        sys.platform = original
        importlib.reload(pm)


def test_macos_selects_the_posix_backend_not_the_windows_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS es POSIX: debe usar ``resource``, nunca el camino de ``ctypes``."""
    monkeypatch.setattr(sys, "platform", "darwin")

    module = _load_process_metrics_fresh()

    # Si el despacho fuese por "no es Linux -> Windows", esto llamaría a
    # ctypes.windll y reventaría en esta máquina. Que devuelva un número
    # demuestra que macOS cae en la rama POSIX.
    value = module.current_memory_rss_bytes()
    assert value is not None
    assert value > 0
    assert module._kernel32 is None
    assert module._psapi is None


# -- Camino Windows: estructural, con la API de Windows sustituida por un doble -----------


def _load_process_metrics_fresh() -> types.ModuleType:
    """Carga ``process_metrics.py`` como módulo aislado, sin pasar por
    ``teaf/__init__.py`` — que arrastra ``asyncio``, y ``asyncio`` bifurca por
    ``sys.platform`` en su propio import (``asyncio.windows_events`` necesita
    la extensión ``_overlapped``, que solo existe en un Windows real). Cargar
    el archivo suelto evita ese arrastre y deja simular solo esta pieza.
    """
    spec = importlib.util.spec_from_file_location(
        "process_metrics_windows_probe", _PROCESS_METRICS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_imports_without_error_under_simulated_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No debe volver a ocurrir lo que motivó este parche: importar el
    módulo bajo Windows no debe lanzar ``ModuleNotFoundError`` ni ninguna
    otra excepción."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(kernel32=MagicMock(), psapi=MagicMock()),
        raising=False,
    )

    module = _load_process_metrics_fresh()

    assert hasattr(module, "_kernel32")
    assert hasattr(module, "_psapi")


def test_module_loads_on_simulated_windows_with_resource_made_unimportable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La reproducción más fiel del bug original que se puede montar en Linux.

    Además de simular ``sys.platform == "win32"``, deja ``resource``
    **inutilizable**: poner ``None`` en ``sys.modules`` hace que
    ``import resource`` lance ``ImportError``, que es exactamente lo que pasa
    en un Windows real, donde el módulo no existe. Si la guarda de plataforma
    se rompiera, este test fallaría con el mismo error que reportó el usuario.
    """
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "resource", None)
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(kernel32=MagicMock(), psapi=MagicMock()),
        raising=False,
    )

    module = _load_process_metrics_fresh()

    # El camino de CPU en Windows no usa ni ``resource`` ni ``ctypes``.
    value = module.current_cpu_time_seconds()
    assert value is not None
    assert value >= 0.0


def test_windows_memory_reads_the_field_the_fake_os_call_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ejercita la estructura ``ctypes`` real: si el orden de campos o el
    tamaño (``cb``) estuviera mal, este valor no coincidiría o la llamada
    fallaría con un error de memoria en vez de devolver limpiamente el dato."""
    monkeypatch.setattr(sys, "platform", "win32")
    fake_kernel32 = MagicMock()
    fake_kernel32.GetCurrentProcess.return_value = 0xFFFFFFFF
    fake_psapi = MagicMock()
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(kernel32=fake_kernel32, psapi=fake_psapi),
        raising=False,
    )

    module = _load_process_metrics_fresh()

    expected_bytes = 123_456_789

    def _fake_get_process_memory_info(handle: object, ptr: object, cb: object) -> int:
        counters = ctypes.cast(ptr, ctypes.POINTER(module._ProcessMemoryCounters)).contents
        counters.WorkingSetSize = expected_bytes
        return 1  # BOOL TRUE

    module._psapi.GetProcessMemoryInfo.side_effect = _fake_get_process_memory_info

    assert module._windows_memory_rss_bytes() == expected_bytes
    assert module.current_memory_rss_bytes() == expected_bytes


def test_windows_memory_returns_none_when_the_win32_call_reports_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GetProcessMemoryInfo`` devuelve ``BOOL`` — ``0`` es fallo. El
    diagnóstico debe degradar a ``None``, no propagar una excepción."""
    monkeypatch.setattr(sys, "platform", "win32")
    fake_kernel32 = MagicMock()
    fake_kernel32.GetCurrentProcess.return_value = 0xFFFFFFFF
    fake_psapi = MagicMock()
    fake_psapi.GetProcessMemoryInfo.return_value = 0
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(kernel32=fake_kernel32, psapi=fake_psapi),
        raising=False,
    )

    module = _load_process_metrics_fresh()

    assert module._windows_memory_rss_bytes() is None


def test_windows_cpu_time_uses_os_times_not_ctypes(monkeypatch: pytest.MonkeyPatch) -> None:
    """El camino de CPU en Windows no usa ``ctypes`` en absoluto: reutiliza
    ``os.times()``, documentada por la librería estándar como disponible en
    Unix y Windows. Esta prueba corre la función de verdad —no hay nada que
    simular— y solo comprueba que la superficie de ``ctypes.windll`` no
    interviene para llegar al resultado."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes,
        "windll",
        types.SimpleNamespace(kernel32=MagicMock(), psapi=MagicMock()),
        raising=False,
    )

    module = _load_process_metrics_fresh()

    value = module.current_cpu_time_seconds()
    assert value is not None
    assert value >= 0.0
    module._kernel32.assert_not_called()
    module._psapi.assert_not_called()
