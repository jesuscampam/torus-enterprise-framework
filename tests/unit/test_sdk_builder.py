"""Pruebas unitarias de backend/sdk/builder.py (ModuleBuilder)."""

from __future__ import annotations

from backend.runtime.capabilities.enums import CapabilityCategory
from backend.runtime.container import Lifetime
from backend.sdk.builder import ModuleBuilder
from backend.sdk.enums import ModuleCategory


class _Greeter:
    pass


def test_builder_defaults() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").build()
    assert manifest.descriptor.id == "demo"
    assert manifest.descriptor.display_name == "demo"
    assert manifest.descriptor.version == "0.0.0"
    assert manifest.descriptor.category is ModuleCategory.GENERIC
    assert manifest.runtime_compatibility == "*"
    assert manifest.sdk_compatibility == "*"


def test_builder_fluent_chain_sets_all_fields() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo", display_name="Demo")
        .with_version("1.0.0")
        .with_description("Módulo de ejemplo")
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.DATABASE)
        .with_tags("db", "sql")
        .with_documentation("docs/demo/DEMO.md")
        .with_runtime_compatibility(">=0.5.0")
        .with_sdk_compatibility(">=1.0.0")
        .as_experimental()
        .as_deprecated()
        .add_capability(
            id="demo.cap", name="demo-cap", category=CapabilityCategory.DATABASE, tags=("db",)
        )
        .add_dependency(module_id="core", version_constraint="1.0.0", optional=True)
        .add_configuration(key="LEVEL", required=True, default="info")
        .add_service(_Greeter, lambda c: _Greeter(), lifetime=Lifetime.TRANSIENT)
        .add_healthcheck(name="demo.ping", description="Ping trivial")
        .add_event("demo.happened")
        .build()
    )

    descriptor = manifest.descriptor
    assert descriptor.version == "1.0.0"
    assert descriptor.description == "Módulo de ejemplo"
    assert descriptor.author == "TEAF Team"
    assert descriptor.category is ModuleCategory.DATABASE
    assert descriptor.tags == ("db", "sql")
    assert descriptor.documentation == "docs/demo/DEMO.md"
    assert descriptor.experimental is True
    assert descriptor.deprecated is True
    assert manifest.license == "MIT"
    assert manifest.runtime_compatibility == ">=0.5.0"
    assert manifest.sdk_compatibility == ">=1.0.0"
    assert len(manifest.capabilities) == 1
    assert manifest.capabilities[0].id == "demo.cap"
    assert len(manifest.dependencies) == 1
    assert manifest.dependencies[0].module_id == "core"
    assert len(manifest.configuration) == 1
    assert manifest.configuration[0].key == "LEVEL"
    assert len(manifest.services) == 1
    assert manifest.services[0].contract is _Greeter
    assert manifest.services[0].lifetime is Lifetime.TRANSIENT
    assert len(manifest.health_checks) == 1
    assert manifest.health_checks[0].name == "demo.ping"
    assert manifest.events == ("demo.happened",)


def test_builder_display_name_defaults_to_name() -> None:
    manifest = ModuleBuilder(id="demo", name="demo-module").build()
    assert manifest.descriptor.display_name == "demo-module"


def test_builder_with_display_name_overrides_default() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_display_name("Demo Module").build()
    assert manifest.descriptor.display_name == "Demo Module"


def test_builder_add_multiple_entries_of_same_kind() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_capability(id="a", name="a")
        .add_capability(id="b", name="b")
        .build()
    )
    assert [c.id for c in manifest.capabilities] == ["a", "b"]
