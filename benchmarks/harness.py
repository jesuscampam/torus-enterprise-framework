"""Instrumentación de medida de los benchmarks de TEAF (Sprint 2.9.1).

Deliberadamente sin dependencias nuevas: ``time.perf_counter`` y
``tracemalloc`` de la librería estándar bastan para lo que hace falta medir
aquí, y añadir ``pytest-benchmark`` o ``asv`` al stack exigiría su propio
ADR ([CLAUDE.md](../CLAUDE.md) §4) a cambio de precisión que no cambiaría
ninguna decisión.

Tres decisiones de método, porque una medida mal tomada es peor que ninguna:

1. **Calentamiento antes de medir.** La primera ejecución de cualquier
   operación paga imports perezosos, construcción de cachés y compilación de
   expresiones regulares. Medirla mezclaría coste de arranque con coste de
   régimen.
2. **Se reporta la mediana y el p95, no la media.** Una media se distorsiona
   con un único pico de GC o de planificación del sistema operativo; la
   mediana describe el caso típico y el p95 la cola que un SLO nota.
3. **La memoria se mide como pico de asignación** (``tracemalloc``) de una
   sola ejecución aislada, no como RSS del proceso: el RSS incluye todo lo
   que el intérprete ya tenía reservado y no distingue qué lo asignó.
"""

from __future__ import annotations

import gc
import statistics
import time
import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

#: Ejecuciones de calentamiento descartadas antes de empezar a medir.
DEFAULT_WARMUP = 5

#: Ejecuciones medidas. 50 da una mediana estable sin que la suite completa
#: tarde más de unos segundos, que es lo que la hace ejecutable en cada PR.
DEFAULT_REPEATS = 50


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Resultado de un benchmark: tiempos en microsegundos, memoria en bytes."""

    name: str
    group: str
    median_us: float
    p95_us: float
    min_us: float
    repeats: int
    peak_memory_bytes: int = 0
    #: Nota libre — p. ej. el tamaño del lote sobre el que se midió.
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "group": self.group,
            "medianUs": round(self.median_us, 3),
            "p95Us": round(self.p95_us, 3),
            "minUs": round(self.min_us, 3),
            "repeats": self.repeats,
            "peakMemoryBytes": self.peak_memory_bytes,
            "note": self.note,
        }


@dataclass
class BenchmarkSuite:
    """Colección de benchmarks de un mismo grupo, con su resultado acumulado."""

    group: str
    results: list[BenchmarkResult] = field(default_factory=list)

    def record(self, result: BenchmarkResult) -> BenchmarkResult:
        self.results.append(result)
        return result


@contextmanager
def _stable_environment() -> Iterator[None]:
    """Desactiva el recolector de basura durante la medida.

    Un ciclo de GC disparado en mitad de una repetición añade decenas de
    microsegundos que no pertenecen a la operación medida — y que caen en
    repeticiones distintas en cada ejecución, haciendo el resultado
    irreproducible. Se recolecta explícitamente antes de empezar y se
    restaura el estado original al terminar.
    """
    was_enabled = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()


def measure(
    name: str,
    operation: Callable[[], Any],
    *,
    group: str,
    warmup: int = DEFAULT_WARMUP,
    repeats: int = DEFAULT_REPEATS,
    note: str = "",
    measure_memory: bool = False,
) -> BenchmarkResult:
    """Mide ``operation`` y devuelve su resultado estadístico.

    ``measure_memory`` activa ``tracemalloc``, que ralentiza la ejecución
    entre 4 y 10 veces — por eso solo se activa en los benchmarks donde el
    consumo de memoria es la magnitud interesante (arranque, registro de
    módulos), nunca en los de latencia pura.
    """
    for _ in range(warmup):
        operation()

    samples: list[float] = []
    with _stable_environment():
        for _ in range(repeats):
            started = time.perf_counter()
            operation()
            samples.append((time.perf_counter() - started) * 1_000_000)

    peak_memory = 0
    if measure_memory:
        gc.collect()
        tracemalloc.start()
        operation()
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    ordered = sorted(samples)
    return BenchmarkResult(
        name=name,
        group=group,
        median_us=statistics.median(ordered),
        p95_us=ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)],
        min_us=ordered[0],
        repeats=repeats,
        peak_memory_bytes=peak_memory,
        note=note,
    )


def format_table(results: list[BenchmarkResult]) -> str:
    """Tabla de texto alineada, agrupada por subsistema."""
    if not results:
        return "(sin resultados)"

    width = max(len(result.name) for result in results) + 2
    lines: list[str] = []
    current_group = ""
    header = f"{'BENCHMARK':<{width}} {'MEDIANA':>12} {'P95':>12} {'MÍNIMO':>12}  NOTA"

    for result in results:
        if result.group != current_group:
            current_group = result.group
            lines.append("")
            lines.append(f"── {current_group} ".ljust(width + 42, "─"))
            lines.append(header)
        lines.append(
            f"{result.name:<{width}} "
            f"{_human_time(result.median_us):>12} "
            f"{_human_time(result.p95_us):>12} "
            f"{_human_time(result.min_us):>12}  "
            f"{result.note}"
        )
    return "\n".join(lines)


def _human_time(microseconds: float) -> str:
    """Formatea microsegundos en la unidad que mejor se lee."""
    if microseconds < 1:
        return f"{microseconds * 1000:.0f} ns"
    if microseconds < 1000:
        return f"{microseconds:.2f} µs"
    return f"{microseconds / 1000:.2f} ms"


def human_bytes(value: int) -> str:
    """Formatea bytes en la unidad que mejor se lee."""
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value / (1024 * 1024):.2f} MiB"
