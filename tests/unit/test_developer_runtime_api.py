"""Pruebas unitarias de backend/developer/runtime_api.py (DeveloperRuntimeAPI)."""

from __future__ import annotations

import asyncio

from teaf._internal.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from teaf._internal.developer.runtime_api import DeveloperRuntimeAPI
from teaf._internal.runtime.capabilities.builder import CapabilityBuilder
from teaf._internal.runtime.features.flag import FeatureFlag
from teaf._internal.runtime.runtime import Runtime


class _Greeter:
    pass


def _running_runtime() -> Runtime:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(name="x", version="1", status=ModuleStatus.IMPLEMENTED))
    runtime = Runtime(registry=registry, framework_version="0.4.0-alpha")
    asyncio.run(runtime.startup())
    return runtime


def test_info_reflects_runtime_diagnostics() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime, configuration_provider=lambda: {"env": "test"})

    info = api.info()

    assert info["frameworkVersion"] == "0.4.0-alpha"
    assert info["configurationSummary"] == {"env": "test"}


def test_modules_lists_registered_modules() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    modules = api.modules()

    assert [m["name"] for m in modules] == ["x"]


def test_services_lists_registered_services() -> None:
    runtime = _running_runtime()
    runtime.register_service(_Greeter, lambda _c: _Greeter())
    api = DeveloperRuntimeAPI(runtime)

    services = api.services()

    assert services[0]["serviceId"] == "_Greeter"


def test_capabilities_lists_registered_capabilities() -> None:
    runtime = _running_runtime()
    runtime.register_capability(CapabilityBuilder(id="demo.cap", name="demo-cap").build())
    api = DeveloperRuntimeAPI(runtime)

    capabilities = api.capabilities()

    assert capabilities[0]["id"] == "demo.cap"


def test_features_lists_registered_feature_flags() -> None:
    runtime = _running_runtime()
    runtime.feature_manager.register(FeatureFlag(id="demo.flag", name="Demo Flag"))
    api = DeveloperRuntimeAPI(runtime)

    features = api.features()

    assert features[0]["id"] == "demo.flag"


def test_plugins_lists_no_plugins_by_default() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    assert api.plugins() == []


def test_events_reflects_event_bus_history() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    events = api.events()

    assert any(event["name"] == "framework.started" for event in events)


def test_events_limit_returns_only_the_most_recent() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    events = api.events(limit=1)

    assert len(events) == 1


def test_configuration_returns_configuration_provider_output() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime, configuration_provider=lambda: {"env": "test"})

    assert api.configuration() == {"env": "test"}


def test_configuration_defaults_to_empty_mapping() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    assert api.configuration() == {}


def test_dependencies_returns_module_and_service_summaries() -> None:
    runtime = _running_runtime()
    api = DeveloperRuntimeAPI(runtime)

    dependencies = api.dependencies()

    assert dependencies["modules"] == {"nodes": 1, "edges": 0}
    assert dependencies["services"] == []
