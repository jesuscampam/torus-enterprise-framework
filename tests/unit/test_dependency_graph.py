"""Pruebas unitarias de backend/runtime/dependency_graph.py (DependencyGraph)."""

from __future__ import annotations

import pytest
from backend.core.registry import ModuleDescriptor, ModuleStatus
from backend.runtime.dependency_graph import DependencyGraph
from backend.runtime.exceptions import CircularDependencyException


def _descriptor(name: str, *dependencies: str) -> ModuleDescriptor:
    return ModuleDescriptor(
        name=name, version="1", status=ModuleStatus.CONTRACTS_ONLY, dependencies=dependencies
    )


def test_topological_order_places_dependencies_before_dependents() -> None:
    graph = DependencyGraph([_descriptor("ai", "security"), _descriptor("security")])

    order = graph.topological_order()

    assert order.index("security") < order.index("ai")


def test_topological_order_with_no_dependencies_includes_all_nodes() -> None:
    graph = DependencyGraph([_descriptor("database"), _descriptor("storage")])

    order = graph.topological_order()

    assert set(order) == {"database", "storage"}


def test_detect_cycle_returns_none_when_acyclic() -> None:
    graph = DependencyGraph([_descriptor("ai", "security"), _descriptor("security")])
    assert graph.detect_cycle() is None


def test_detect_cycle_finds_direct_cycle() -> None:
    graph = DependencyGraph([_descriptor("a", "b"), _descriptor("b", "a")])

    cycle = graph.detect_cycle()

    assert cycle is not None
    assert set(cycle) == {"a", "b"}


def test_topological_order_raises_on_cycle() -> None:
    graph = DependencyGraph([_descriptor("a", "b"), _descriptor("b", "a")])

    with pytest.raises(CircularDependencyException):
        graph.topological_order()


def test_dependency_on_unregistered_module_is_ignored() -> None:
    # "core" no está registrado como módulo (ver application.py) — no debe
    # romper el grafo ni aparecer como nodo.
    graph = DependencyGraph([_descriptor("security", "core")])

    assert graph.edges()["security"] == ()
    assert "core" not in graph.nodes()
    assert graph.topological_order() == ("security",)


def test_nodes_returns_all_module_names() -> None:
    graph = DependencyGraph([_descriptor("a"), _descriptor("b")])
    assert set(graph.nodes()) == {"a", "b"}
