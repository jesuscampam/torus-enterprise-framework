"""Runner de la suite de benchmarks de TEAF (Sprint 2.9.1).

    python -m benchmarks                     # ejecuta todo y compara con la baseline
    python -m benchmarks --suite di events   # solo esas suites
    python -m benchmarks --save-baseline     # fija la baseline actual
    python -m benchmarks --json resultados.json

La comparación contra `benchmarks/baseline.json` es lo que convierte la
suite en una red de seguridad y no en un número suelto: un cambio que
degrade una operación más allá del umbral sale marcado y hace fallar el
comando, igual que un test.

Los tres parámetros de la comparación no son arbitrarios; salen de medir la
varianza real de esta suite ejecutándola tres veces seguidas **sin tocar el
código** (Sprint 2.9.1, tabla completa en
[docs/BENCHMARKS.md](../docs/BENCHMARKS.md)):

1. **Se compara el mínimo, no la mediana.** El ruido de planificación y de
   GC es unilateral: puede hacer que una operación tarde más, nunca menos.
   El mínimo de N repeticiones converge por tanto al coste real, mientras
   que la mediana arrastra el ruido. Medido: la dispersión entre ejecuciones
   idénticas baja de 88% a 41% en el peor caso, y mejora en 17 de los 25
   benchmarks.
2. **Umbral relativo del 60%** (`--tolerance`). La dispersión observada sin
   cambio alguno de código llega al 52% en los benchmarks dominados por
   asignación de memoria (compresión GZip, bootstrap de módulo, arranque
   ASGI). Un umbral por debajo de eso no detecta regresiones: produce falsos
   positivos hasta que alguien deja de mirar el resultado.
3. **Suelo absoluto de 1 µs** (`NOISE_FLOOR_US`). En operaciones de
   centenares de nanosegundos, un único cambio de contexto duplica la
   medida: `register()` oscila un 41% en reposo, pero solo 0.29 µs en
   absoluto. Exigir ambas condiciones — relativa *y* absoluta — evita que el
   ruido de las operaciones más rápidas dispare la puerta.

Conviene ser explícito sobre el límite que esto impone: en un contenedor
compartido esta suite detecta regresiones de orden de magnitud, que son las
que rompen producción, y **no** detecta degradaciones finas del 10-20% en
las operaciones pesadas. Para eso haría falta una máquina dedicada.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from benchmarks.harness import BenchmarkResult, format_table, human_bytes
from benchmarks.suites import ALL_SUITES

BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"

#: Degradación relativa a partir de la cual una operación se considera una
#: regresión. Ver el docstring del módulo para por qué es tan ancho.
DEFAULT_TOLERANCE = 0.60

#: Degradación absoluta mínima para reportar nada, en microsegundos. Una
#: operación de 400 ns no puede "empeorar un 60%" de forma significativa:
#: eso son 240 ns, por debajo del ruido de un cambio de contexto.
NOISE_FLOOR_US = 1.0


def _environment() -> dict[str, str]:
    """Datos de la máquina — dos ejecuciones solo son comparables si coinciden."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
    }


def run_grouped(
    selected: tuple[str, ...] = (), *, quiet: bool = False
) -> dict[str, list[BenchmarkResult]]:
    """Ejecuta las suites pedidas y devuelve sus resultados por nombre de suite.

    Conservar de qué suite viene cada resultado es lo que permite volver a
    medir solo lo sospechoso en ``confirm_regressions`` sin repetir la suite
    entera.
    """
    grouped: dict[str, list[BenchmarkResult]] = {}
    for name, suite in ALL_SUITES:
        if selected and name not in selected:
            continue
        if not quiet:
            print(f"  ejecutando {name}...", file=sys.stderr)
        grouped[name] = suite()
    return grouped


def run(selected: tuple[str, ...] = (), *, quiet: bool = False) -> list[BenchmarkResult]:
    """Ejecuta las suites pedidas (todas si no se pide ninguna), aplanadas."""
    return [result for results in run_grouped(selected, quiet=quiet).values() for result in results]


def confirm_regressions(
    suspects: set[str],
    origin: dict[str, list[BenchmarkResult]],
    baseline: dict[str, object],
    *,
    tolerance: float,
) -> tuple[list[str], list[str]]:
    """Vuelve a medir los benchmarks sospechosos. Devuelve ``(confirmadas, descartadas)``.

    Existe porque el contenedor es compartido: un pico del anfitrión durante
    una sola repetición puede multiplicar por 2.5 el mínimo de un benchmark
    que en aislamiento es estable dentro del 5% (observado en Sprint 2.9.1
    con «Arranque ASGI completo»: 5.2 ms en tres ejecuciones seguidas, 13.3
    ms en una cuarta sin cambio alguno de código). Subir el umbral hasta
    cubrir ese caso dejaría pasar regresiones reales; volver a medir, no.

    Solo se repiten las suites que contienen algún sospechoso, así que el
    coste es proporcional al problema y no se paga cuando todo va bien. Una
    regresión real es reproducible por definición; si no lo es, era ruido.
    """
    suites_to_repeat = tuple(
        suite
        for suite, results in origin.items()
        if any(result.name in suspects for result in results)
    )
    print(
        f"\n⟳ Reintentando {len(suspects)} benchmark(s) sospechoso(s) para "
        "descartar ruido del anfitrión...",
        file=sys.stderr,
    )
    repeated = [result for result in run(suites_to_repeat, quiet=True) if result.name in suspects]
    confirmed, _ = compare(repeated, baseline, tolerance=tolerance)
    confirmed_names = {line.split(":", 1)[0] for line in confirmed}
    return confirmed, sorted(suspects - confirmed_names)


def compare(
    results: list[BenchmarkResult], baseline: dict[str, object], *, tolerance: float
) -> tuple[list[str], list[str]]:
    """Compara contra la baseline. Devuelve ``(regresiones, mejoras)``.

    Se compara el **mínimo** de cada benchmark, no la mediana, y se exige
    que la diferencia supere a la vez el umbral relativo y el suelo
    absoluto ``NOISE_FLOOR_US``. El porqué de ambas decisiones, con las
    medidas que las respaldan, está en el docstring del módulo.

    Las baselines anteriores a Sprint 2.9.1 solo guardaban ``medianUs``; se
    acepta como respaldo para no invalidarlas, aunque sea peor estadístico.
    """
    entries = baseline.get("results")
    if not isinstance(entries, list):
        return [], []
    previous = {
        str(entry["name"]): float(entry.get("minUs", entry["medianUs"]))
        for entry in entries
        if isinstance(entry, dict) and "name" in entry and ("minUs" in entry or "medianUs" in entry)
    }

    regressions: list[str] = []
    improvements: list[str] = []
    for result in results:
        before = previous.get(result.name)
        if before is None or before <= 0:
            continue
        difference = result.min_us - before
        if abs(difference) < NOISE_FLOOR_US:
            continue
        delta = difference / before
        line = f"{result.name}: {before:.2f} µs → {result.min_us:.2f} µs ({delta:+.0%})"
        if delta > tolerance:
            regressions.append(line)
        elif delta < -tolerance:
            improvements.append(line)
    return regressions, improvements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Suite de benchmarks de TEAF.")
    parser.add_argument(
        "--suite", nargs="*", default=[], help="Suites a ejecutar (por defecto, todas)."
    )
    parser.add_argument(
        "--save-baseline", action="store_true", help="Fija estos resultados como baseline."
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="Escribe los resultados en un JSON."
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"Degradación relativa tolerada (por defecto {DEFAULT_TOLERANCE}).",
    )
    parser.add_argument("--no-compare", action="store_true", help="No compara contra la baseline.")
    args = parser.parse_args(argv)

    grouped = run_grouped(tuple(args.suite))
    results = [result for suite_results in grouped.values() for result in suite_results]
    print(format_table(results))

    with_memory = [r for r in results if r.peak_memory_bytes]
    if with_memory:
        print("\n── Memoria (pico de asignación de una ejecución) ".ljust(70, "─"))
        for result in with_memory:
            print(f"{result.name:<40} {human_bytes(result.peak_memory_bytes):>12}")

    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "environment": _environment(),
        "results": [result.as_dict() for result in results],
    }

    if args.json is not None:
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"\nResultados escritos en {args.json}")

    if args.save_baseline:
        BASELINE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"\nBaseline fijada en {BASELINE_PATH}")
        return 0

    if args.no_compare or not BASELINE_PATH.exists():
        return 0

    baseline = json.loads(BASELINE_PATH.read_text())
    regressions, improvements = compare(results, baseline, tolerance=args.tolerance)

    if improvements:
        print(f"\n✅ Mejoras (>{args.tolerance:.0%}):")
        for line in improvements:
            print(f"   {line}")

    if regressions:
        suspects = {line.split(":", 1)[0] for line in regressions}
        confirmed, discarded = confirm_regressions(
            suspects, grouped, baseline, tolerance=args.tolerance
        )
        if discarded:
            print("\nℹ️  Descartadas por no reproducirse al volver a medir (ruido del anfitrión):")
            for name in discarded:
                print(f"   {name}")
        if confirmed:
            print(f"\n❌ Regresiones confirmadas (>{args.tolerance:.0%} frente a la baseline):")
            for line in confirmed:
                print(f"   {line}")
            return 1

    print(f"\n✅ Sin regresiones frente a la baseline (tolerancia {args.tolerance:.0%}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
