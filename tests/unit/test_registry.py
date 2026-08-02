"""Pruebas unitarias de backend/core/registry.py (ModuleRegistry)."""

from __future__ import annotations

import pytest
from backend.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus


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
