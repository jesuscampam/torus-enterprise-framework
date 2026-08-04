"""Pruebas unitarias de las extensiones de Sprint 2.4 sobre ``Runtime``.

Cubre los wrappers de orquestación (``register_*``/``remove_*``/``resolve_*``,
cada uno con su evento), ``diagnostics()`` y ``self_description()`` — ver
backend/runtime/runtime.py.
"""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from teaf._internal.runtime.capabilities.builder import CapabilityBuilder
from teaf._internal.runtime.container import Lifetime
from teaf._internal.runtime.exceptions import (
    CapabilityNotFoundException,
    FeatureNotFoundException,
    PluginValidationException,
    ServiceNotRegisteredException,
)
from teaf._internal.runtime.features.flag import FeatureFlag
from teaf._internal.runtime.plugin_loader import Plugin
from teaf._internal.runtime.runtime import Runtime


class _Greeter:
    pass


class _FakePlugin(Plugin):
    def __init__(self, name: str = "fake-plugin", version: str = "1.0.0") -> None:
        self.name = name
        self.version = version

    def register(self, container: object) -> None:  # noqa: ARG002
        pass


def _events(runtime: Runtime, *names: str) -> list[str]:
    received: list[str] = []
    for name in names:
        runtime.event_bus.subscribe(name, lambda e: received.append(e.name))
    return received


def test_register_module_delegates_and_publishes_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received = _events(runtime, "module.registered")

    runtime.register_module(
        ModuleDescriptor(name="x", version="1", status=ModuleStatus.IMPLEMENTED)
    )

    assert runtime.modules[0].name == "x"
    assert received == ["module.registered"]


def test_unregister_module_delegates_and_publishes_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    runtime.register_module(
        ModuleDescriptor(name="x", version="1", status=ModuleStatus.IMPLEMENTED)
    )
    received = _events(runtime, "module.unregistered")

    runtime.unregister_module("x")

    assert runtime.modules == ()
    assert received == ["module.unregistered"]


def test_register_service_resolve_and_remove_publish_events() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received = _events(runtime, "service.registered", "service.resolved", "service.removed")

    runtime.register_service(_Greeter, lambda _c: _Greeter())
    instance = runtime.resolve_service(_Greeter)
    runtime.remove_service(_Greeter)

    assert isinstance(instance, _Greeter)
    assert received == ["service.registered", "service.resolved", "service.removed"]
    with pytest.raises(ServiceNotRegisteredException):
        runtime.resolve_service(_Greeter)


def test_register_service_supports_scoped_and_transient_lifetimes() -> None:
    runtime = Runtime(registry=ModuleRegistry())

    class _Scoped:
        pass

    class _Transient:
        pass

    runtime.register_service(_Scoped, lambda _c: _Scoped(), lifetime=Lifetime.SCOPED)
    runtime.register_service(_Transient, lambda _c: _Transient(), lifetime=Lifetime.TRANSIENT)

    with runtime.container.create_scope() as scope:
        assert isinstance(scope.resolve(_Scoped), _Scoped)
    assert isinstance(runtime.resolve_service(_Transient), _Transient)


def test_register_capability_and_remove_publish_events() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received = _events(runtime, "capability.registered", "capability.removed")
    capability = CapabilityBuilder(id="demo.cap", name="demo-cap").build()

    runtime.register_capability(capability)
    runtime.remove_capability("demo.cap")

    assert received == ["capability.registered", "capability.removed"]
    with pytest.raises(CapabilityNotFoundException):
        runtime.capability_registry.describe("demo.cap")


def test_load_plugin_and_unload_publish_events() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received = _events(runtime, "plugin.loaded", "plugin.unloaded")

    runtime.load_plugin(_FakePlugin())
    runtime.unload_plugin("fake-plugin")

    assert received == ["plugin.loaded", "plugin.unloaded"]
    with pytest.raises(PluginValidationException):
        runtime.unload_plugin("fake-plugin")


def test_enable_and_disable_feature_publish_events() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    runtime.feature_manager.register(FeatureFlag(id="demo.flag", name="Demo Flag"))
    received = _events(runtime, "feature.enabled", "feature.disabled")

    runtime.enable_feature("demo.flag")
    assert runtime.feature_manager.is_enabled("demo.flag") is True

    runtime.disable_feature("demo.flag")
    assert runtime.feature_manager.is_enabled("demo.flag") is False

    assert received == ["feature.enabled", "feature.disabled"]
    with pytest.raises(FeatureNotFoundException):
        runtime.enable_feature("does-not-exist")


def test_startup_publishes_framework_started_alongside_legacy_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received = _events(runtime, "framework.started", "framework.startup.completed")

    asyncio.run(runtime.startup())

    assert received == ["framework.started", "framework.startup.completed"]


def test_shutdown_publishes_framework_stopped_alongside_legacy_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    asyncio.run(runtime.startup())
    received = _events(runtime, "framework.stopped", "framework.shutdown.completed")

    asyncio.run(runtime.shutdown())

    assert received == ["framework.stopped", "framework.shutdown.completed"]


def test_diagnostics_before_startup_has_no_startup_time() -> None:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.4.0-alpha")

    diagnostics = runtime.diagnostics()

    assert diagnostics.startup_time is None
    assert diagnostics.running_time_seconds == 0.0
    assert diagnostics.framework_version == "0.4.0-alpha"
    assert diagnostics.memory_placeholder == "not-implemented"
    assert diagnostics.cpu_placeholder == "not-implemented"


def test_diagnostics_after_startup_reflects_counts_and_configuration() -> None:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(name="x", version="1", status=ModuleStatus.IMPLEMENTED))
    runtime = Runtime(registry=registry, framework_version="0.4.0-alpha")
    asyncio.run(runtime.startup())

    runtime.register_service(_Greeter, lambda _c: _Greeter())
    runtime.register_capability(CapabilityBuilder(id="demo.cap", name="demo-cap").build())
    runtime.feature_manager.register(FeatureFlag(id="demo.flag", name="Demo Flag"))
    runtime.load_plugin(_FakePlugin())

    diagnostics = runtime.diagnostics(configuration_summary={"env": "test"})

    assert diagnostics.startup_time is not None
    assert diagnostics.running_time_seconds >= 0.0
    assert diagnostics.registered_modules == 1
    assert diagnostics.registered_services == 1
    assert diagnostics.registered_capabilities == 1
    assert diagnostics.registered_plugins == 1
    assert diagnostics.registered_features == 1
    assert diagnostics.configuration_summary == {"env": "test"}
    assert diagnostics.dependency_graph_summary == {"nodes": 1, "edges": 0}
    assert diagnostics.container_statistics == {"registeredContracts": 1}
    payload = diagnostics.as_dict()
    assert payload["runtimeId"] == diagnostics.runtime_id


def test_self_description_reflects_runtime_state() -> None:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(name="ai", version="1", status=ModuleStatus.CONTRACTS_ONLY))
    registry.register(
        ModuleDescriptor(name="database", version="1", status=ModuleStatus.CONTRACTS_ONLY)
    )
    runtime = Runtime(registry=registry, framework_version="0.4.0-alpha")
    asyncio.run(runtime.startup())

    description = runtime.self_description()

    assert description.framework == "TEAF"
    assert description.version == "0.4.0-alpha"
    assert description.runtime_state == "running"
    assert set(description.modules) == {"ai", "database"}
    assert description.supports_ai is True
    assert description.supports_database is True
    assert description.supports_mcp is False
    assert description.supports_scheduler is False
    assert description.supports_storage is False
    assert description.supports_notifications is False

    payload = description.as_dict()
    supports = payload["supports"]
    assert isinstance(supports, dict)
    assert supports["ai"] is True
    assert payload["framework"] == "TEAF"


def test_framework_version_defaults_when_not_provided() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    assert runtime.framework_version == "0.0.0"
