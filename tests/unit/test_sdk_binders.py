"""Pruebas unitarias de backend/sdk/service_binder.py y backend/sdk/capability_binder.py."""

from __future__ import annotations

import pytest
from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.capability import ModuleCapability
from teaf._internal.sdk.capability_binder import CapabilityBinder
from teaf._internal.sdk.exceptions import ModuleRegistrationException
from teaf._internal.sdk.service import ModuleService
from teaf._internal.sdk.service_binder import ServiceBinder


class _Greeter:
    pass


def test_service_binder_registers_service_with_derived_metadata() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    service = ModuleService(
        contract=_Greeter,
        factory=lambda c: _Greeter(),
        lifetime=Lifetime.SCOPED,
        description="Saluda",
        tags=("demo",),
        capabilities=("demo.greet",),
    )

    ServiceBinder().bind([service], runtime=runtime, module_id="demo")

    assert runtime.container.is_registered(_Greeter) is True
    metadata = runtime.service_discovery.describe("demo._Greeter")
    assert metadata.module == "demo"
    assert metadata.lifetime is Lifetime.SCOPED
    assert metadata.description == "Saluda"
    assert metadata.tags == ("demo",)
    assert metadata.capabilities == ("demo.greet",)


def test_service_binder_binds_multiple_services() -> None:
    class _Other:
        pass

    runtime = Runtime(registry=ModuleRegistry())
    services = [
        ModuleService(contract=_Greeter, factory=lambda c: _Greeter()),
        ModuleService(contract=_Other, factory=lambda c: _Other()),
    ]

    ServiceBinder().bind(services, runtime=runtime, module_id="demo")

    assert runtime.container.is_registered(_Greeter) is True
    assert runtime.container.is_registered(_Other) is True


def test_capability_binder_registers_capability_with_provider_and_module() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    capability = ModuleCapability(
        id="demo.greet", name="demo-greet", category=CapabilityCategory.AI
    )

    CapabilityBinder().bind([capability], runtime=runtime, module_id="demo")

    registered = runtime.capability_registry.describe("demo.greet")
    assert registered.metadata.provider == "demo"
    assert registered.metadata.module == "demo"
    assert registered.metadata.category is CapabilityCategory.AI


def test_capability_binder_propagates_experimental_flag() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    capability = ModuleCapability(id="demo.beta", name="demo-beta", experimental=True)

    CapabilityBinder().bind([capability], runtime=runtime, module_id="demo")

    assert runtime.capability_registry.describe("demo.beta").metadata.experimental is True


def test_capability_binder_raises_on_duplicate() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    capability = ModuleCapability(id="demo.greet", name="demo-greet")
    CapabilityBinder().bind([capability], runtime=runtime, module_id="demo")

    with pytest.raises(ModuleRegistrationException):
        CapabilityBinder().bind([capability], runtime=runtime, module_id="demo")
