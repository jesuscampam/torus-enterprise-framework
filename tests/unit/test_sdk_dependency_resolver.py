"""Pruebas unitarias de backend/sdk/dependency_resolver.py (ModuleDependencyResolver)."""

from __future__ import annotations

import pytest
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.dependency_resolver import ModuleDependencyResolver
from teaf._internal.sdk.exceptions import ModuleDependencyException


def test_resolve_orders_dependencies_before_dependents() -> None:
    a = ModuleBuilder(id="a", name="a").add_dependency(module_id="b").build()
    b = ModuleBuilder(id="b", name="b").build()

    order = ModuleDependencyResolver([a, b]).resolve()

    assert order == ("b", "a")


def test_resolve_handles_modules_without_dependencies() -> None:
    a = ModuleBuilder(id="a", name="a").build()
    b = ModuleBuilder(id="b", name="b").build()

    order = ModuleDependencyResolver([a, b]).resolve()

    assert set(order) == {"a", "b"}


def test_detect_cycle_returns_none_when_acyclic() -> None:
    a = ModuleBuilder(id="a", name="a").add_dependency(module_id="b").build()
    b = ModuleBuilder(id="b", name="b").build()

    assert ModuleDependencyResolver([a, b]).detect_cycle() is None


def test_detect_cycle_finds_circular_dependency() -> None:
    x = ModuleBuilder(id="x", name="x").add_dependency(module_id="y").build()
    y = ModuleBuilder(id="y", name="y").add_dependency(module_id="x").build()

    cycle = ModuleDependencyResolver([x, y]).detect_cycle()

    assert cycle is not None
    assert "x" in cycle
    assert "y" in cycle


def test_resolve_raises_on_cycle() -> None:
    x = ModuleBuilder(id="x", name="x").add_dependency(module_id="y").build()
    y = ModuleBuilder(id="y", name="y").add_dependency(module_id="x").build()

    with pytest.raises(ModuleDependencyException):
        ModuleDependencyResolver([x, y]).resolve()


def test_detect_conflicts_finds_distinct_version_pins() -> None:
    p = (
        ModuleBuilder(id="p", name="p")
        .add_dependency(module_id="shared", version_constraint="1.0.0")
        .build()
    )
    q = (
        ModuleBuilder(id="q", name="q")
        .add_dependency(module_id="shared", version_constraint="2.0.0")
        .build()
    )

    conflicts = ModuleDependencyResolver([p, q]).detect_conflicts()

    assert len(conflicts) == 1
    assert "shared" in conflicts[0]


def test_detect_conflicts_allows_matching_version_pins() -> None:
    p = (
        ModuleBuilder(id="p", name="p")
        .add_dependency(module_id="shared", version_constraint="1.0.0")
        .build()
    )
    q = (
        ModuleBuilder(id="q", name="q")
        .add_dependency(module_id="shared", version_constraint="1.0.0")
        .build()
    )

    assert ModuleDependencyResolver([p, q]).detect_conflicts() == ()


def test_detect_conflicts_ignores_unpinned_dependencies() -> None:
    p = ModuleBuilder(id="p", name="p").add_dependency(module_id="shared").build()
    q = (
        ModuleBuilder(id="q", name="q")
        .add_dependency(module_id="shared", version_constraint="1.0.0")
        .build()
    )

    assert ModuleDependencyResolver([p, q]).detect_conflicts() == ()


def test_resolve_raises_on_conflict_before_checking_cycles() -> None:
    p = (
        ModuleBuilder(id="p", name="p")
        .add_dependency(module_id="shared", version_constraint="1.0.0")
        .build()
    )
    q = (
        ModuleBuilder(id="q", name="q")
        .add_dependency(module_id="shared", version_constraint="2.0.0")
        .build()
    )

    with pytest.raises(ModuleDependencyException, match="Conflicto"):
        ModuleDependencyResolver([p, q]).resolve()


def test_dependency_tree_expands_known_modules() -> None:
    a = ModuleBuilder(id="a", name="a").add_dependency(module_id="b").build()
    b = ModuleBuilder(id="b", name="b").build()

    tree = ModuleDependencyResolver([a, b]).dependency_tree("a")

    assert tree == {"id": "a", "dependencies": [{"id": "b", "dependencies": []}]}


def test_dependency_tree_leaves_unknown_dependency_unexpanded() -> None:
    a = ModuleBuilder(id="a", name="a").add_dependency(module_id="unregistered").build()

    tree = ModuleDependencyResolver([a]).dependency_tree("a")

    assert tree == {"id": "a", "dependencies": [{"id": "unregistered", "dependencies": []}]}


def test_dependency_tree_protects_against_cycles() -> None:
    x = ModuleBuilder(id="x", name="x").add_dependency(module_id="y").build()
    y = ModuleBuilder(id="y", name="y").add_dependency(module_id="x").build()

    tree = ModuleDependencyResolver([x, y]).dependency_tree("x")

    assert tree["id"] == "x"
    assert tree["dependencies"][0]["id"] == "y"  # type: ignore[index]


def test_dependency_tree_unknown_module_raises() -> None:
    with pytest.raises(ModuleDependencyException):
        ModuleDependencyResolver([]).dependency_tree("does-not-exist")
