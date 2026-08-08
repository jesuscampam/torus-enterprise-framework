"""Detector de dependencias circulares entre módulos de ``teaf/`` (Sprint 2.9.1).

Complementa a los otros dos verificadores estáticos del repositorio:

- ``check_public_api_boundary.py`` vigila que nadie *de fuera* importe
  ``teaf._internal``.
- ``check_internal_namespace.py`` vigila que no quede rastro del antiguo
  paquete ``backend``.
- **este** vigila la forma del grafo interno: que no haya ciclos, y que las
  dependencias entre capas apunten en la dirección que fija
  [ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md).

Analiza con ``ast``, sin ejecutar ningún código: un ciclo de imports que solo
se manifiesta en tiempo de ejecución (imports diferidos dentro de funciones)
no es lo que se busca aquí — lo que se busca es el ciclo *estructural*, el
que indica que dos módulos se conocen mutuamente y ya no se pueden razonar
por separado.

    python scripts/check_circular_dependencies.py
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: Raíz analizada. Solo se siguen imports internos: los de terceros y los de
#: la librería estándar no pueden formar un ciclo *con* TEAF.
PACKAGE_ROOT = "teaf"

#: Excepción arquitectónica declarada, no un descuido. ``core/application.py``
#: es el *composition root* del framework (el componente "Main" de Clean
#: Architecture): el único lugar autorizado a conocer y conectar todas las
#: capas para ensamblar la aplicación. Ver el docstring de ese archivo y
#: FRAMEWORK-BLUEPRINT.md, sección 11.
COMPOSITION_ROOTS: frozenset[str] = frozenset({"teaf._internal.core.application"})


def module_name_of(path: Path) -> str:
    """Nombre de módulo punteado de ``path``, relativo a la raíz del repositorio."""
    relative = path.relative_to(REPOSITORY_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports_of(source: str, *, module: str) -> set[str]:
    """Módulos internos que ``source`` importa a nivel estático.

    Los imports relativos se resuelven contra ``module`` para poder
    compararlos con los absolutos.
    """
    found: set[str] = set()
    tree = ast.parse(source)
    package_parts = module.split(".")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(PACKAGE_ROOT):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - node.level + 1]
                target = ".".join([*base, node.module] if node.module else base)
            else:
                target = node.module or ""
            if target.startswith(PACKAGE_ROOT):
                found.add(target)
    return found


def build_graph(root: Path) -> dict[str, set[str]]:
    """Grafo dirigido ``módulo -> módulos que importa``."""
    graph: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        module = module_name_of(path)
        graph[module] = imports_of(path.read_text(encoding="utf-8"), module=module)
    return graph


def _resolve(target: str, known: Iterable[str]) -> str | None:
    """Mapea un import a un módulo real del grafo.

    ``from teaf._internal.core.logging import get_logger`` importa el módulo
    ``teaf._internal.core.logging``; ``from teaf._internal.core import x``
    importa el paquete. Se busca la coincidencia más larga.
    """
    known_set = set(known)
    if target in known_set:
        return target
    parent = target.rsplit(".", 1)[0]
    return parent if parent in known_set else None


def find_cycles(graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Ciclos del grafo, cada uno como la lista de módulos que lo forman.

    Búsqueda en profundidad con marcado tricolor (sin visitar / en curso /
    terminado) — la misma técnica que ``DependencyGraph`` usa para los
    módulos del Runtime, aquí sobre los imports de Python.
    """
    cycles: list[list[str]] = []
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(module: str) -> None:
        state[module] = 1
        stack.append(module)
        for raw_target in sorted(graph.get(module, ())):
            target = _resolve(raw_target, graph)
            if target is None or target == module:
                continue
            if target in COMPOSITION_ROOTS or module in COMPOSITION_ROOTS:
                continue
            if state.get(target, 0) == 1:
                cycle = stack[stack.index(target) :] + [target]
                if cycle not in cycles:
                    cycles.append(cycle)
            elif state.get(target, 0) == 0:
                visit(target)
        stack.pop()
        state[module] = 2

    for module in sorted(graph):
        if state.get(module, 0) == 0:
            visit(module)
    return cycles


def main() -> int:
    graph = build_graph(REPOSITORY_ROOT / PACKAGE_ROOT)
    cycles = find_cycles(graph)

    if cycles:
        print(f"❌ {len(cycles)} ciclo(s) de dependencias encontrado(s):")
        for cycle in cycles:
            print("   " + " → ".join(cycle))
        return 1

    print(f"OK — sin ciclos de dependencias entre los {len(graph)} módulos de '{PACKAGE_ROOT}'.")
    return 0


if __name__ == "__main__":
    sys.setrecursionlimit(10_000)
    raise SystemExit(main())
