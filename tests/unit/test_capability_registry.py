"""Pruebas unitarias de backend/runtime/capabilities/ (Capability Model)."""

from __future__ import annotations

import pytest
from teaf._internal.runtime.capabilities.builder import CapabilityBuilder
from teaf._internal.runtime.capabilities.enums import (
    CapabilityCategory,
    CapabilityHealth,
    CapabilityStatus,
)
from teaf._internal.runtime.capabilities.metadata import CapabilityMetadata
from teaf._internal.runtime.capabilities.provider_registry import CapabilityProviderRegistry
from teaf._internal.runtime.capabilities.registry import CapabilityRegistry
from teaf._internal.runtime.exceptions import (
    CapabilityAlreadyRegisteredException,
    CapabilityNotFoundException,
)


def test_builder_applies_defaults() -> None:
    capability = CapabilityBuilder(id="x", name="x").build()

    assert capability.metadata.category is CapabilityCategory.CUSTOM
    assert capability.metadata.status is CapabilityStatus.REGISTERED
    assert capability.metadata.experimental is False
    assert capability.metadata.deprecated is False
    assert capability.metadata.health is CapabilityHealth.UNKNOWN


def test_builder_fluent_chain_sets_all_fields() -> None:
    capability = (
        CapabilityBuilder(id="database.query", name="database-query")
        .with_display_name("Consulta de base de datos")
        .with_description("Ejecuta consultas")
        .with_version("1.0.0")
        .with_category(CapabilityCategory.DATABASE)
        .with_provider("postgres")
        .with_module("database")
        .with_status(CapabilityStatus.ACTIVE)
        .with_owner("platform-team")
        .with_tags("sql", "database")
        .with_documentation("docs/database/DATABASE.md")
        .with_permissions_required("database.read")
        .with_configuration_required("DATABASE_URL")
        .with_dependencies("core")
        .as_experimental()
        .as_deprecated()
        .build()
    )

    metadata = capability.metadata
    assert metadata.display_name == "Consulta de base de datos"
    assert metadata.category is CapabilityCategory.DATABASE
    assert metadata.provider == "postgres"
    assert metadata.module == "database"
    assert metadata.status is CapabilityStatus.ACTIVE
    assert metadata.owner == "platform-team"
    assert metadata.tags == ("sql", "database")
    assert metadata.permissions_required == ("database.read",)
    assert metadata.configuration_required == ("DATABASE_URL",)
    assert metadata.dependencies == ("core",)
    assert metadata.experimental is True
    assert metadata.deprecated is True


def test_capability_metadata_as_dict_is_serializable() -> None:
    metadata = CapabilityMetadata(id="x", name="x", display_name="X")
    payload = metadata.as_dict()

    assert payload["id"] == "x"
    assert payload["category"] == "custom"
    assert payload["status"] == "registered"
    assert payload["health"] == "unknown"
    assert isinstance(payload["createdAt"], str)


def test_registry_register_and_find() -> None:
    registry = CapabilityRegistry()
    capability = CapabilityBuilder(id="x", name="x").build()

    registry.register(capability)

    assert registry.exists("x") is True
    assert registry.find("x") is capability


def test_registry_register_duplicate_raises() -> None:
    registry = CapabilityRegistry()
    capability = CapabilityBuilder(id="x", name="x").build()
    registry.register(capability)

    with pytest.raises(CapabilityAlreadyRegisteredException):
        registry.register(capability)


def test_registry_unregister_removes_capability() -> None:
    registry = CapabilityRegistry()
    capability = CapabilityBuilder(id="x", name="x").build()
    registry.register(capability)

    registry.unregister("x")

    assert registry.exists("x") is False


def test_registry_unregister_unknown_raises() -> None:
    registry = CapabilityRegistry()
    with pytest.raises(CapabilityNotFoundException):
        registry.unregister("does-not-exist")


def test_registry_describe_unknown_raises() -> None:
    registry = CapabilityRegistry()
    with pytest.raises(CapabilityNotFoundException):
        registry.describe("does-not-exist")


def test_registry_describe_returns_registered_capability() -> None:
    registry = CapabilityRegistry()
    capability = CapabilityBuilder(id="x", name="x").build()
    registry.register(capability)

    assert registry.describe("x") is capability


def test_builder_with_health_check_sets_callable() -> None:
    capability = (
        CapabilityBuilder(id="x", name="x")
        .with_health_check(lambda: CapabilityHealth.HEALTHY)
        .build()
    )

    assert capability.health_check is not None
    assert capability.health_check() is CapabilityHealth.HEALTHY


def test_registry_list_filters_by_category() -> None:
    registry = CapabilityRegistry()
    db_capability = (
        CapabilityBuilder(id="db.query", name="db-query")
        .with_category(CapabilityCategory.DATABASE)
        .build()
    )
    ai_capability = (
        CapabilityBuilder(id="ai.generate", name="ai-generate")
        .with_category(CapabilityCategory.AI)
        .build()
    )
    registry.register(db_capability)
    registry.register(ai_capability)

    assert registry.list(category=CapabilityCategory.DATABASE) == (db_capability,)
    assert len(registry.list()) == 2
    assert db_capability in registry.list()
    assert ai_capability in registry.list()


def test_registry_search_matches_id_name_display_name_and_tags() -> None:
    registry = CapabilityRegistry()
    capability = (
        CapabilityBuilder(id="database.query", name="database-query")
        .with_display_name("Consulta")
        .with_tags("sql")
        .build()
    )
    registry.register(capability)

    assert registry.search("database") == (capability,)
    assert registry.search("consulta") == (capability,)
    assert registry.search("sql") == (capability,)
    assert registry.search("does-not-match") == ()


def test_provider_registry_discovers_capabilities_from_all_providers() -> None:
    class _Provider:
        def __init__(self, capabilities: list[object]) -> None:
            self._capabilities = capabilities

        def get_capabilities(self) -> list[object]:
            return self._capabilities

    registry = CapabilityProviderRegistry()
    registry.register("a", _Provider(["cap-a"]))
    registry.register("b", _Provider(["cap-b1", "cap-b2"]))

    assert set(registry.list_providers()) == {"a", "b"}
    assert registry.discover_all_capabilities() == ("cap-a", "cap-b1", "cap-b2")


def test_provider_registry_register_duplicate_raises() -> None:
    class _Provider:
        def get_capabilities(self) -> list[object]:
            return []

    registry = CapabilityProviderRegistry()
    registry.register("a", _Provider())

    with pytest.raises(ValueError, match="a"):
        registry.register("a", _Provider())


def test_provider_registry_unregister_is_idempotent() -> None:
    registry = CapabilityProviderRegistry()
    registry.unregister("does-not-exist")  # no debe lanzar
