"""Pruebas unitarias de backend/core/registry.py (ModuleRegistry)."""

from __future__ import annotations

import pytest
from teaf._internal.core.registry import (
    ModuleDescriptor,
    ModuleLifecycleState,
    ModuleRegistry,
    ModuleStatus,
)


def test_register_and_get() -> None:
    registry = ModuleRegistry()
    descriptor = ModuleDescriptor(
        name="database", version="0.2.0-alpha", status=ModuleStatus.CONTRACTS_ONLY
    )

    registry.register(descriptor)

    assert registry.get("database") == descriptor


def test_get_unknown_module_returns_none() -> None:
    registry = ModuleRegistry()
    assert registry.get("does-not-exist") is None


def test_list_modules_preserves_registration_order() -> None:
    registry = ModuleRegistry()
    first = ModuleDescriptor(name="a", version="1", status=ModuleStatus.CONTRACTS_ONLY)
    second = ModuleDescriptor(name="b", version="1", status=ModuleStatus.CONTRACTS_ONLY)

    registry.register(first)
    registry.register(second)

    assert registry.list_modules() == (first, second)


def test_register_duplicate_name_raises_value_error() -> None:
    registry = ModuleRegistry()
    descriptor = ModuleDescriptor(name="database", version="1", status=ModuleStatus.CONTRACTS_ONLY)
    registry.register(descriptor)

    with pytest.raises(ValueError, match="database"):
        registry.register(descriptor)


def test_independent_registries_do_not_share_state() -> None:
    first_registry = ModuleRegistry()
    second_registry = ModuleRegistry()

    first_registry.register(
        ModuleDescriptor(name="x", version="1", status=ModuleStatus.CONTRACTS_ONLY)
    )

    assert second_registry.get("x") is None
    assert second_registry.list_modules() == ()


def test_unregister_removes_module() -> None:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(name="x", version="1", status=ModuleStatus.IMPLEMENTED))

    registry.unregister("x")

    assert registry.get("x") is None
    assert registry.list_modules() == ()


def test_unregister_unknown_module_raises_value_error() -> None:
    registry = ModuleRegistry()
    with pytest.raises(ValueError, match="does-not-exist"):
        registry.unregister("does-not-exist")


def test_module_descriptor_id_aliases_name() -> None:
    descriptor = ModuleDescriptor(name="database", version="1", status=ModuleStatus.IMPLEMENTED)
    assert descriptor.id == "database"


def test_module_descriptor_defaults() -> None:
    descriptor = ModuleDescriptor(name="x", version="1", status=ModuleStatus.CONTRACTS_ONLY)

    assert descriptor.author is None
    assert descriptor.description == ""
    assert descriptor.lifecycle_state is ModuleLifecycleState.REGISTERED
    assert descriptor.capabilities == ()
    assert descriptor.tags == ()
    assert descriptor.documentation is None
    assert descriptor.experimental is False


def test_module_descriptor_as_dict_is_serializable() -> None:
    descriptor = ModuleDescriptor(
        name="ai",
        version="0.4.0-alpha",
        status=ModuleStatus.CONTRACTS_ONLY,
        dependencies=("security",),
        author="TEAF Team",
        description="Módulo de IA",
        lifecycle_state=ModuleLifecycleState.ACTIVE,
        capabilities=("ai.generate",),
        tags=("ai",),
        documentation="docs/ai/AI.md",
        experimental=True,
    )

    payload = descriptor.as_dict()

    assert payload["id"] == "ai"
    assert payload["name"] == "ai"
    assert payload["author"] == "TEAF Team"
    assert payload["description"] == "Módulo de IA"
    assert payload["status"] == "contracts_only"
    assert payload["lifecycleState"] == "active"
    assert payload["capabilities"] == ["ai.generate"]
    assert payload["dependencies"] == ["security"]
    assert payload["tags"] == ["ai"]
    assert payload["documentation"] == "docs/ai/AI.md"
    assert payload["experimental"] is True
    assert isinstance(payload["createdAt"], str)
    assert isinstance(payload["updatedAt"], str)
