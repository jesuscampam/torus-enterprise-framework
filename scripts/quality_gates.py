"""Puertas de calidad de TEAF — todas, en un solo comando (Sprint 2.9.1).

    python scripts/quality_gates.py              # todas las puertas
    python scripts/quality_gates.py --fast       # salta las lentas (tests, ejemplos, benchmarks)
    python scripts/quality_gates.py --list       # qué puertas hay
    python scripts/quality_gates.py --gate lint mypy

Hasta este Sprint, verificar el repositorio significaba recordar y ejecutar
ocho comandos distintos en el orden correcto. Eso funciona mientras alguien
se acuerde de todos; deja de funcionar exactamente el día en que importa.
Este script es la lista, ejecutable.

Cada puerta declara **por qué** existe además de qué comprueba: una puerta
cuyo motivo nadie recuerda acaba desactivándose en cuanto molesta. El
resumen final indica cuáles pasaron, cuáles fallaron y cuánto tardó cada
una, y el código de salida es distinto de cero si alguna falló — apto para
CI sin envoltorio adicional.

Relación con [docs/standards/QUALITY-GATES.md](../docs/standards/QUALITY-GATES.md):
ese documento es la fuente de verdad de *qué se exige* y por qué; este
script es su ejecución automática. Cuando difieran, manda el documento.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: Cobertura mínima exigida sobre ``teaf/``. Ver QUALITY-GATES.md.
MINIMUM_COVERAGE = 95


@dataclass(frozen=True, slots=True)
class Gate:
    """Una puerta de calidad: su comando, su motivo y cuánto suele costar."""

    name: str
    description: str
    command: list[str]
    #: ``True`` si tarda lo bastante como para saltarla en un bucle rápido de
    #: desarrollo (``--fast``). No significa opcional: en CI corren todas.
    slow: bool = False
    env: dict[str, str] = field(default_factory=dict)


#: Las puertas, en el orden en que conviene ejecutarlas: primero las baratas
#: que fallan pronto (formato, lint, tipos), luego las que necesitan que el
#: código sea al menos importable, y al final las lentas.
GATES: tuple[Gate, ...] = (
    Gate(
        name="format",
        description="black — formato uniforme; evita diffs de estilo que ocultan cambios reales.",
        command=["black", "--check", "."],
    ),
    Gate(
        name="lint",
        description="ruff — errores de sintaxis, imports sin usar y orden de imports.",
        command=["ruff", "check", "."],
    ),
    Gate(
        name="mypy",
        description=(
            "mypy --strict sobre teaf/ — tipos completos. Se invoca como 'python -m mypy' "
            "a propósito: el ejecutable suelto no encuentra los tipos de FastAPI/Starlette "
            "y los degrada a Any, dejando pasar errores reales (Sprint 2.9.1)."
        ),
        command=[sys.executable, "-m", "mypy", "--strict", "teaf"],
    ),
    Gate(
        name="imports",
        description="Sin ciclos de dependencias entre los módulos internos.",
        command=[sys.executable, "scripts/check_circular_dependencies.py"],
    ),
    Gate(
        name="namespace",
        description="El paquete privado sigue siendo teaf._internal, sin rastro de 'backend'.",
        command=[sys.executable, "scripts/check_internal_namespace.py"],
    ),
    Gate(
        name="boundary",
        description="Ningún ejemplo importa teaf._internal — la API pública basta.",
        command=[sys.executable, "scripts/check_public_api_boundary.py", "examples/"],
    ),
    Gate(
        name="public-api",
        description="La API pública no rompe compatibilidad hacia atrás (firmas, no solo nombres).",
        command=[sys.executable, "scripts/check_public_api_surface.py"],
    ),
    Gate(
        name="startup",
        description="La aplicación arranca de verdad y sus endpoints de sistema responden.",
        command=[sys.executable, "scripts/check_runtime_startup.py"],
    ),
    Gate(
        name="build",
        description=(
            "El paquete se construye y el wheel contiene lo que debe. Es la única puerta "
            "que mira el artefacto distribuible y no el árbol de fuentes (Sprint 3.0)."
        ),
        command=[sys.executable, "scripts/check_package_build.py"],
        slow=True,
    ),
    Gate(
        name="dependencies",
        description=(
            "pip-audit — vulnerabilidades conocidas en las dependencias. Falla ante cualquier "
            "aviso no aceptado explícitamente en docs/security/accepted-vulnerabilities.json "
            "(Sprint 2.9.2)."
        ),
        command=[sys.executable, "scripts/check_dependency_audit.py"],
        slow=True,
    ),
    Gate(
        name="tests",
        description=f"Suite completa con cobertura ≥{MINIMUM_COVERAGE}% sobre teaf/.",
        command=[
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=teaf",
            f"--cov-fail-under={MINIMUM_COVERAGE}",
            "--cov-report=term:skip-covered",
        ],
        slow=True,
    ),
    Gate(
        name="benchmarks",
        description="Sin regresiones de rendimiento frente a la baseline documentada.",
        command=[sys.executable, "-m", "benchmarks"],
        slow=True,
    ),
)


def run_gate(gate: Gate) -> tuple[bool, float, str]:
    """Ejecuta una puerta. Devuelve ``(pasó, segundos, salida)``."""
    started = time.perf_counter()
    completed = subprocess.run(
        gate.command,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, elapsed, output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Puertas de calidad de TEAF.")
    parser.add_argument("--fast", action="store_true", help="Salta las puertas lentas.")
    parser.add_argument("--list", action="store_true", help="Lista las puertas y termina.")
    parser.add_argument("--gate", nargs="*", default=[], help="Ejecuta solo estas puertas.")
    args = parser.parse_args(argv)

    if args.list:
        for gate in GATES:
            marca = " (lenta)" if gate.slow else ""
            print(f"  {gate.name:<12}{marca}\n      {gate.description}")
        return 0

    selected = [
        gate
        for gate in GATES
        if (not args.gate or gate.name in args.gate) and not (args.fast and gate.slow)
    ]

    print(f"Ejecutando {len(selected)} puerta(s) de calidad...\n")
    results: list[tuple[Gate, bool, float, str]] = []

    for gate in selected:
        print(f"── {gate.name} ".ljust(72, "─"))
        passed, elapsed, output = run_gate(gate)
        results.append((gate, passed, elapsed, output))
        if passed:
            print(f"   ✅ {gate.name} ({elapsed:.1f}s)")
        else:
            print(f"   ❌ {gate.name} ({elapsed:.1f}s)")
            print("\n".join(f"      {line}" for line in output.strip().splitlines()[-25:]))
        print()

    failed = [gate.name for gate, passed, _, _ in results if not passed]
    total = sum(elapsed for _, _, elapsed, _ in results)

    print("═" * 72)
    for gate, passed, elapsed, _ in results:
        marca = "✅" if passed else "❌"
        print(f"  {marca} {gate.name:<14} {elapsed:>7.1f}s   {gate.description[:44]}")
    print("═" * 72)

    if failed:
        print(
            f"\n❌ {len(failed)} puerta(s) fallida(s): {', '.join(failed)}  "
            f"({total:.1f}s en total)"
        )
        return 1
    print(f"\n✅ Las {len(results)} puertas de calidad pasan.  ({total:.1f}s en total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
