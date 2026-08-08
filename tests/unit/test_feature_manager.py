"""Pruebas unitarias de backend/runtime/features/ (Feature Flags)."""

from __future__ import annotations

import pytest
from teaf._internal.runtime.exceptions import (
    FeatureAlreadyRegisteredException,
    FeatureNotFoundException,
)
from teaf._internal.runtime.features.enums import FeatureGroup, FeatureStatus
from teaf._internal.runtime.features.flag import FeatureFlag
from teaf._internal.runtime.features.manager import FeatureManager


def test_register_and_exists() -> None:
    manager = FeatureManager()
    flag = FeatureFlag(id="ai.embeddings", name="AI Embeddings", group=FeatureGroup.AI)

    manager.register(flag)

    assert manager.exists("ai.embeddings") is True
    assert manager.describe("ai.embeddings") == flag


def test_register_duplicate_raises() -> None:
    manager = FeatureManager()
    flag = FeatureFlag(id="x", name="X")
    manager.register(flag)

    with pytest.raises(FeatureAlreadyRegisteredException):
        manager.register(flag)


def test_new_flag_defaults_to_disabled() -> None:
    manager = FeatureManager()
    manager.register(FeatureFlag(id="x", name="X"))

    assert manager.is_enabled("x") is False


def test_enable_and_disable_toggle_status() -> None:
    manager = FeatureManager()
    manager.register(FeatureFlag(id="x", name="X"))

    manager.enable("x")
    assert manager.is_enabled("x") is True
    assert manager.describe("x").status is FeatureStatus.ENABLED

    manager.disable("x")
    assert manager.is_enabled("x") is False
    assert manager.describe("x").status is FeatureStatus.DISABLED


def test_enable_unknown_feature_raises() -> None:
    manager = FeatureManager()
    with pytest.raises(FeatureNotFoundException):
        manager.enable("does-not-exist")


def test_disable_unknown_feature_raises() -> None:
    manager = FeatureManager()
    with pytest.raises(FeatureNotFoundException):
        manager.disable("does-not-exist")


def test_describe_unknown_feature_raises() -> None:
    manager = FeatureManager()
    with pytest.raises(FeatureNotFoundException):
        manager.describe("does-not-exist")


def test_is_enabled_unknown_feature_raises() -> None:
    manager = FeatureManager()
    with pytest.raises(FeatureNotFoundException):
        manager.is_enabled("does-not-exist")


def test_list_filters_by_group() -> None:
    manager = FeatureManager()
    ai_flag = FeatureFlag(id="ai.x", name="AI X", group=FeatureGroup.AI)
    security_flag = FeatureFlag(id="security.x", name="Security X", group=FeatureGroup.SECURITY)
    manager.register(ai_flag)
    manager.register(security_flag)

    assert manager.list(group=FeatureGroup.AI) == (ai_flag,)
    assert set(manager.list()) == {ai_flag, security_flag}


def test_enable_updates_updated_at_timestamp() -> None:
    manager = FeatureManager()
    manager.register(FeatureFlag(id="x", name="X"))
    before = manager.describe("x").updated_at

    manager.enable("x")

    assert manager.describe("x").updated_at >= before


def test_feature_flag_as_dict_is_serializable() -> None:
    flag = FeatureFlag(
        id="ai.embeddings",
        name="AI Embeddings",
        description="Embeddings vectoriales",
        group=FeatureGroup.AI,
        status=FeatureStatus.ENABLED,
        tags=("ai", "beta"),
    )

    payload = flag.as_dict()

    assert payload["id"] == "ai.embeddings"
    assert payload["group"] == "ai"
    assert payload["status"] == "enabled"
    assert payload["tags"] == ["ai", "beta"]
    assert isinstance(payload["createdAt"], str)


def test_feature_group_values() -> None:
    assert FeatureGroup.PLATFORM.value == "platform"
    assert FeatureGroup.SECURITY.value == "security"
    assert FeatureGroup.DATABASE.value == "database"
    assert FeatureGroup.AI.value == "ai"
    assert FeatureGroup.MCP.value == "mcp"
    assert FeatureGroup.EXPERIMENTAL.value == "experimental"
    assert FeatureGroup.INFRASTRUCTURE.value == "infrastructure"
