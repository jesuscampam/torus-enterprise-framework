"""Pruebas unitarias de las primitivas del Module SDK (backend/sdk/)."""

from __future__ import annotations

import pytest
from backend.runtime.capabilities.enums import CapabilityCategory, CapabilityHealth
from backend.runtime.container import Lifetime
from backend.sdk.capability import ModuleCapability
from backend.sdk.configuration import ModuleConfiguration
from backend.sdk.dependency import ModuleDependency
from backend.sdk.descriptor import ModuleDescriptor
from backend.sdk.enums import ModuleCategory
from backend.sdk.health import ModuleHealth
from backend.sdk.lifecycle import CANONICAL_ORDER, ModuleLifecycle, ModuleLifecycleState
from backend.sdk.service import ModuleService


def test_module_descriptor_as_dict_is_serializable() -> None:
    descriptor = ModuleDescriptor(
        id="demo",
        name="demo",
        display_name="Demo",
        version="0.1.0",
        category=ModuleCategory.DATABASE,
        tags=("db",),
    )
    payload = descriptor.as_dict()
    assert payload["id"] == "demo"
    assert payload["category"] == "database"
    assert payload["tags"] == ["db"]


def test_module_configuration_hides_sensitive_default() -> None:
    entry = ModuleConfiguration(key="SECRET", default="hunter2", sensitive=True)
    assert entry.as_dict()["default"] is None


def test_module_configuration_exposes_non_sensitive_default() -> None:
    entry = ModuleConfiguration(key="LEVEL", default="info", sensitive=False)
    assert entry.as_dict()["default"] == "info"


def test_module_health_reports_has_check() -> None:
    with_check = ModuleHealth(name="ping", check=lambda: CapabilityHealth.HEALTHY)
    without_check = ModuleHealth(name="ping")
    assert with_check.as_dict()["hasCheck"] is True
    assert without_check.as_dict()["hasCheck"] is False


def test_module_capability_as_dict() -> None:
    capability = ModuleCapability(
        id="demo.cap", name="demo-cap", category=CapabilityCategory.AI, tags=("ai",)
    )
    payload = capability.as_dict()
    assert payload["id"] == "demo.cap"
    assert payload["category"] == "ai"
    assert payload["tags"] == ["ai"]


def test_module_service_as_dict_excludes_factory() -> None:
    class Greeter:
        pass

    service = ModuleService(contract=Greeter, factory=lambda c: Greeter(), lifetime=Lifetime.SCOPED)
    payload = service.as_dict()
    assert payload["contract"] == "Greeter"
    assert payload["lifetime"] == "scoped"
    assert "factory" not in payload


def test_module_dependency_as_dict() -> None:
    dependency = ModuleDependency(module_id="core", version_constraint=">=1.0.0", optional=True)
    assert dependency.as_dict() == {
        "moduleId": "core",
        "versionConstraint": ">=1.0.0",
        "optional": True,
    }


def test_module_lifecycle_starts_created() -> None:
    lifecycle = ModuleLifecycle()
    assert lifecycle.state is ModuleLifecycleState.CREATED
    assert lifecycle.history == (ModuleLifecycleState.CREATED,)


def test_module_lifecycle_advances_in_canonical_order() -> None:
    lifecycle = ModuleLifecycle()
    for state in CANONICAL_ORDER[1:]:
        lifecycle.advance(state)
    assert lifecycle.state is ModuleLifecycleState.DISPOSED
    assert lifecycle.history == CANONICAL_ORDER


def test_module_lifecycle_rejects_backward_transition() -> None:
    lifecycle = ModuleLifecycle()
    lifecycle.advance(ModuleLifecycleState.INITIALIZED)
    lifecycle.advance(ModuleLifecycleState.CONFIGURED)
    with pytest.raises(ValueError, match="retrocede"):
        lifecycle.advance(ModuleLifecycleState.INITIALIZED)


def test_module_lifecycle_failed_is_terminal() -> None:
    lifecycle = ModuleLifecycle()
    lifecycle.advance(ModuleLifecycleState.FAILED)
    with pytest.raises(ValueError, match="falló"):
        lifecycle.advance(ModuleLifecycleState.INITIALIZED)


def test_module_lifecycle_failed_reachable_from_any_state() -> None:
    lifecycle = ModuleLifecycle()
    lifecycle.advance(ModuleLifecycleState.INITIALIZED)
    lifecycle.advance(ModuleLifecycleState.FAILED)
    assert lifecycle.state is ModuleLifecycleState.FAILED


def test_module_lifecycle_as_dict() -> None:
    lifecycle = ModuleLifecycle()
    lifecycle.advance(ModuleLifecycleState.INITIALIZED)
    payload = lifecycle.as_dict()
    assert payload["state"] == "initialized"
    assert payload["history"] == ["created", "initialized"]
