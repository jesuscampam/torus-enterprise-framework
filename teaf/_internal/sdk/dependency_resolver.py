"""``ModuleDependencyResolver`` — resuelve dependencias entre varios ``ModuleManifest``.

Reutiliza el algoritmo de ``backend.runtime.dependency_graph.DependencyGraph``
(Kahn / DFS ya probado en Sprint 2.3) en vez de reimplementar detección de
ciclos — ``DependencyGraph`` solo exige objetos con ``.name``/``.dependencies``
estructuralmente, así que se adapta con ``_GraphNode`` local sin acoplar el
SDK a ``backend.core.registry.ModuleDescriptor`` (cuyos otros campos no
tienen sentido aquí). La detección de conflictos de versión, en cambio, es
exclusiva del SDK — ``DependencyGraph`` no conoce ``version_constraint``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from teaf._internal.runtime.dependency_graph import DependencyGraph
from teaf._internal.runtime.exceptions import CircularDependencyException
from teaf._internal.sdk.exceptions import ModuleDependencyException
from teaf._internal.sdk.manifest import ModuleManifest


@dataclass(frozen=True, slots=True)
class _GraphNode:
    """Adaptador estructural: lo único que ``DependencyGraph`` necesita de un módulo."""

    name: str
    dependencies: tuple[str, ...]


class ModuleDependencyResolver:
    """Resuelve el orden de inicialización de un conjunto de módulos y detecta problemas."""

    def __init__(self, manifests: Iterable[ModuleManifest]) -> None:
        self._manifests = {m.descriptor.id: m for m in manifests}

    def detect_cycle(self) -> tuple[str, ...] | None:
        """Devuelve el primer ciclo encontrado (ids en orden), o ``None`` si no hay ninguno."""
        return self._graph().detect_cycle()

    def detect_conflicts(self) -> tuple[str, ...]:
        """Devuelve los conflictos de versión encontrados.

        Un conflicto ocurre cuando dos o más módulos declaran una
        dependencia sobre el mismo ``module_id`` con ``version_constraint``
        exactos (pines) distintos — no se resuelve álgebra de rangos.
        """
        pins: dict[str, dict[str, str]] = {}
        for manifest in self._manifests.values():
            for dependency in manifest.dependencies:
                if dependency.version_constraint is None:
                    continue
                pins.setdefault(dependency.module_id, {})[
                    manifest.descriptor.id
                ] = dependency.version_constraint

        conflicts: list[str] = []
        for module_id, pinned_by in pins.items():
            distinct_versions = set(pinned_by.values())
            if len(distinct_versions) <= 1:
                continue
            detail = ", ".join(f"{dep}={ver}" for dep, ver in sorted(pinned_by.items()))
            conflicts.append(f"Conflicto de versión en '{module_id}': {detail}")
        return tuple(conflicts)

    def resolve(self) -> tuple[str, ...]:
        """Orden de inicialización válido (cada módulo tras sus dependencias).

        Raises:
            ModuleDependencyException: si hay un ciclo o un conflicto de versión.
        """
        conflicts = self.detect_conflicts()
        if conflicts:
            raise ModuleDependencyException("; ".join(conflicts))
        try:
            return self._graph().topological_order()
        except CircularDependencyException as exc:
            raise ModuleDependencyException(str(exc)) from exc

    def dependency_tree(self, module_id: str) -> dict[str, object]:
        """Árbol de dependencias de ``module_id``, expandido recursivamente.

        Un ``module_id`` referenciado pero no incluido en este resolver
        aparece como hoja sin expandir. Protegido contra ciclos.

        Raises:
            ModuleDependencyException: si ``module_id`` no está en este resolver.
        """
        if module_id not in self._manifests:
            raise ModuleDependencyException(f"El módulo '{module_id}' no está en el resolver.")
        return self._build_tree(module_id, visited=set())

    def _build_tree(self, module_id: str, *, visited: set[str]) -> dict[str, object]:
        if module_id in visited or module_id not in self._manifests:
            return {"id": module_id, "dependencies": []}
        visited = visited | {module_id}
        manifest = self._manifests[module_id]
        children = [
            self._build_tree(dependency.module_id, visited=visited)
            for dependency in manifest.dependencies
        ]
        return {"id": module_id, "dependencies": children}

    def _graph(self) -> DependencyGraph:
        nodes = [
            _GraphNode(name=manifest.descriptor.id, dependencies=self._dependency_ids(manifest))
            for manifest in self._manifests.values()
        ]
        return DependencyGraph(nodes)  # type: ignore[arg-type]

    @staticmethod
    def _dependency_ids(manifest: ModuleManifest) -> tuple[str, ...]:
        return tuple(dependency.module_id for dependency in manifest.dependencies)
