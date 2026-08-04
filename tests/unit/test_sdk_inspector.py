"""Pruebas unitarias de backend/sdk/inspector.py (ModuleInspector)."""

from __future__ import annotations

from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.inspector import ModuleInspector
from teaf._internal.sdk.lifecycle import ModuleLifecycleState
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


class _Greeter:
    pass


class _DemoModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="demo", name="demo", display_name="Demo")
            .add_capability(id="demo.cap", name="demo-cap")
            .add_service(_Greeter, lambda c: _Greeter())
            .add_dependency(module_id="core")
            .add_configuration(key="LEVEL")
            .add_healthcheck(name="demo.ping")
            .add_event("demo.happened")
            .build()
        )


def test_manifest_returns_module_manifest() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert inspector.manifest().descriptor.id == "demo"


def test_describe_includes_manifest_and_lifecycle() -> None:
    module = _DemoModule()
    inspector = ModuleInspector(module)

    payload = inspector.describe()

    assert payload["id"] == "demo"
    assert payload["lifecycle"] == {"state": "created", "history": ["created"]}


def test_describe_reflects_current_lifecycle_state() -> None:
    module = _DemoModule()
    module.lifecycle.advance(ModuleLifecycleState.INITIALIZED)
    inspector = ModuleInspector(module)

    payload = inspector.describe()

    assert payload["lifecycle"]["state"] == "initialized"  # type: ignore[index]


def test_services_returns_declared_services() -> None:
    inspector = ModuleInspector(_DemoModule())
    services = inspector.services()
    assert len(services) == 1
    assert services[0].contract is _Greeter


def test_capabilities_returns_declared_capabilities() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert [c.id for c in inspector.capabilities()] == ["demo.cap"]


def test_dependencies_returns_declared_dependencies() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert [d.module_id for d in inspector.dependencies()] == ["core"]


def test_events_returns_declared_events() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert inspector.events() == ("demo.happened",)


def test_configuration_returns_declared_configuration() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert [c.key for c in inspector.configuration()] == ["LEVEL"]


def test_health_returns_declared_healthchecks() -> None:
    inspector = ModuleInspector(_DemoModule())
    assert [h.name for h in inspector.health()] == ["demo.ping"]
