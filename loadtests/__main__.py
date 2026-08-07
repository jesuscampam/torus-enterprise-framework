"""Runner de las pruebas de carga de TEAF (Sprint 2.9.1).

    python -m loadtests                          # los nueve escenarios
    python -m loadtests --scenario health security
    python -m loadtests --requests 5000 --concurrency 64
    python -m loadtests --json resultados.json

A diferencia de [`benchmarks/`](../benchmarks/README.md), esto **no** es una
puerta de calidad y no falla por rendimiento: el rendimiento absoluto en un
contenedor compartido no es un umbral defendible, y una puerta que falla
por el ruido del anfitrión acaba desactivada. Sí falla cuando aparecen
**errores**, que sí son deterministas: una petición que devuelve 500 bajo
concurrencia es un defecto tanto si la máquina va rápida como si va lenta.

Los números de rendimiento se publican en
[docs/PERFORMANCE.md](../docs/PERFORMANCE.md) para poder compararlos entre
versiones a mano, que es el uso realista de esta suite.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

from loadtests.harness import (
    DEFAULT_CONCURRENCY,
    DEFAULT_REQUESTS,
    LoadResult,
    format_table,
    run_scenario,
)
from loadtests.scenarios import ALL_SCENARIOS


async def run(selected: tuple[str, ...], *, requests: int, concurrency: int) -> list[LoadResult]:
    """Ejecuta los escenarios pedidos, uno detrás de otro.

    En serie a propósito: dos escenarios concurrentes compartirían CPU y las
    métricas de ambos serían inservibles.
    """
    results: list[LoadResult] = []
    for scenario in ALL_SCENARIOS:
        if selected and scenario.name not in selected:
            continue
        print(f"  ejecutando {scenario.name}...", file=sys.stderr)
        results.append(await run_scenario(scenario, requests=requests, concurrency=concurrency))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pruebas de carga de TEAF.")
    parser.add_argument(
        "--scenario", nargs="*", default=[], help="Escenarios a ejecutar (por defecto, todos)."
    )
    parser.add_argument("--requests", type=int, default=DEFAULT_REQUESTS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--json", type=Path, default=None, help="Vuelca los resultados a un JSON.")
    parser.add_argument("--list", action="store_true", help="Lista los escenarios y termina.")
    args = parser.parse_args(argv)

    if args.list:
        for scenario in ALL_SCENARIOS:
            print(f"  {scenario.name:<22} {scenario.description}")
        return 0

    results = asyncio.run(
        run(tuple(args.scenario), requests=args.requests, concurrency=args.concurrency)
    )
    if not results:
        print("No coincidió ningún escenario.")
        return 1

    print()
    print(format_table(results))
    print(
        f"\n{args.requests:,} peticiones por escenario, {args.concurrency} en vuelo. "
        "RPS medido en proceso sobre el transporte ASGI: no es la cifra de un "
        "despliegue real (ver el docstring de loadtests/harness.py)."
    )

    if args.json is not None:
        payload = {
            "generatedAt": datetime.now(UTC).isoformat(),
            "environment": {
                "python": platform.python_version(),
                "system": platform.system(),
                "machine": platform.machine(),
            },
            "requests": args.requests,
            "concurrency": args.concurrency,
            "results": [result.as_dict() for result in results],
        }
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"Resultados escritos en {args.json}")

    failed = [result for result in results if result.errors]
    if failed:
        print("\n❌ Escenarios con errores bajo carga:")
        for result in failed:
            reparto = ", ".join(
                f"{code}×{count}" for code, count in sorted(result.status_counts.items())
            )
            print(f"   {result.name}: {result.errors:,} error(es)   [{reparto}]")
        return 1

    print("\n✅ Ningún error bajo carga en ningún escenario.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
