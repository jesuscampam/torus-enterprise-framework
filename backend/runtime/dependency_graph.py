"""``DependencyGraph`` — grafo de dependencias entre módulos registrados.

Construido a partir de ``ModuleDescriptor.dependencies`` (ver
``backend/core/registry.py``). El Runtime lo consulta durante el arranque
(``Runtime.startup()``) para detectar ciclos **antes** de ejecutar el
``StartupPipeline`` — un ciclo aborta el arranque con un error claro en vez
de fallar de forma confusa a mitad de la inicialización.
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.core.registry import ModuleDescriptor
from backend.runtime.exceptions import CircularDependencyException


class DependencyGraph:
    """Grafo dirigido: cada nodo es un módulo, cada arista apunta a una dependencia."""

    def __init__(self, descriptors: Iterable[ModuleDescriptor]) -> None:
        self._nodes: dict[str, ModuleDescriptor] = {d.name: d for d in descriptors}

    def nodes(self) -> tuple[str, ...]:
        """Nombres de todos los módulos del grafo."""
        return tuple(self._nodes)

    def edges(self) -> dict[str, tuple[str, ...]]:
        """Mapa módulo → sus dependencias declaradas.

        Las dependencias que no correspondan a un módulo presente en el
        grafo se ignoran (se asumen externas/ya satisfechas — por ejemplo,
        "core" no se registra como módulo pero sí puede citarse).
        """
        return {
            name: tuple(dep for dep in descriptor.dependencies if dep in self._nodes)
            for name, descriptor in self._nodes.items()
        }

    def detect_cycle(self) -> tuple[str, ...] | None:
        """Devuelve el primer ciclo encontrado (nombres en orden), o ``None`` si no hay ninguno."""
        edges = self.edges()
        state: dict[str, int] = {}  # 0=no visitado, 1=en curso, 2=terminado
        path: list[str] = []

        def visit(node: str) -> tuple[str, ...] | None:
            state[node] = 1
            path.append(node)
            for neighbor in edges.get(node, ()):
                if state.get(neighbor, 0) == 0:
                    cycle = visit(neighbor)
                    if cycle is not None:
                        return cycle
                elif state.get(neighbor) == 1:
                    cycle_start = path.index(neighbor)
                    return tuple(path[cycle_start:]) + (neighbor,)
            path.pop()
            state[node] = 2
            return None

        for node in self._nodes:
            if state.get(node, 0) == 0:
                cycle = visit(node)
                if cycle is not None:
                    return cycle
        return None

    def topological_order(self) -> tuple[str, ...]:
        """Orden válido de inicialización: cada módulo aparece después de sus dependencias.

        Raises:
            CircularDependencyException: si el grafo tiene un ciclo.
        """
        cycle = self.detect_cycle()
        if cycle is not None:
            raise CircularDependencyException(
                f"Dependencia circular entre módulos: {' -> '.join(cycle)}"
            )

        edges = self.edges()
        # in_degree[x] = cuántos módulos deben inicializarse antes que x, es
        # decir, len(edges[x]) (x depende de esos módulos).
        in_degree = {name: len(deps) for name, deps in edges.items()}
        ready = sorted(name for name, degree in in_degree.items() if degree == 0)
        order: list[str] = []

        # dependents[d] = módulos que declaran a d como dependencia.
        dependents: dict[str, list[str]] = {name: [] for name in self._nodes}
        for name, deps in edges.items():
            for dep in deps:
                dependents[dep].append(name)

        while ready:
            current = ready.pop(0)
            order.append(current)
            for dependent in sorted(dependents[current]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)

        return tuple(order)
