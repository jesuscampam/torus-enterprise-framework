"""Pruebas unitarias de backend/runtime/discovery.py (ModuleDiscovery)."""

from __future__ import annotations

from teaf._internal.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from teaf._internal.runtime.discovery import ModuleDiscovery


def _registry_with(*descriptors: ModuleDescriptor) -> ModuleRegistry:
    registry = ModuleRegistry()
    for descriptor in descriptors:
        registry.register(descriptor)
    return registry


def test_discover_returns_all_modules_by_default() -> None:
    registry = _registry_with(
        ModuleDescriptor(name="database", version="1", status=ModuleStatus.CONTRACTS_ONLY),
        ModuleDescriptor(name="security", version="1", status=ModuleStatus.IMPLEMENTED),
    )
    discovery = ModuleDiscovery(registry)

    discovered = discovery.discover()

    assert {d.name for d in discovered} == {"database", "security"}


def test_discover_filters_by_status() -> None:
    registry = _registry_with(
        ModuleDescriptor(name="database", version="1", status=ModuleStatus.CONTRACTS_ONLY),
        ModuleDescriptor(name="security", version="1", status=ModuleStatus.IMPLEMENTED),
    )
    discovery = ModuleDiscovery(registry)

    only_implemented = discovery.discover(status=ModuleStatus.IMPLEMENTED)

    assert [d.name for d in only_implemented] == ["security"]


def test_discover_on_empty_registry_returns_empty_tuple() -> None:
    discovery = ModuleDiscovery(ModuleRegistry())
    assert discovery.discover() == ()
