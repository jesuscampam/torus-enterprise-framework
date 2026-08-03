"""Pruebas unitarias de backend/runtime/plugin_loader.py (Plugin, PluginLoader)."""

from __future__ import annotations

import pytest
from backend.runtime.container import ServiceContainer
from backend.runtime.exceptions import PluginValidationException
from backend.runtime.plugin_loader import Plugin, PluginLifecycleState, PluginLoader, PluginMetadata


class _FakePlugin(Plugin):
    def __init__(self, name: str = "fake-plugin", version: str = "1.0.0") -> None:
        self.name = name
        self.version = version
        self.registered_with: ServiceContainer | None = None

    def register(self, container: ServiceContainer) -> None:
        self.registered_with = container


class _NamelessPlugin(Plugin):
    name = ""
    version = "1.0.0"

    def register(self, container: ServiceContainer) -> None:
        pass


def test_plugin_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        Plugin()  # type: ignore[abstract]


def test_load_registers_plugin_against_container() -> None:
    loader = PluginLoader()
    container = ServiceContainer()
    plugin = _FakePlugin()

    loader.load(plugin, container=container)

    assert plugin.registered_with is container
    assert loader.is_loaded("fake-plugin") is True
    assert loader.list_loaded() == (plugin,)


def test_validate_rejects_plugin_without_name() -> None:
    loader = PluginLoader()
    with pytest.raises(PluginValidationException):
        loader.validate(_NamelessPlugin())


def test_load_rejects_duplicate_plugin_name() -> None:
    loader = PluginLoader()
    container = ServiceContainer()
    loader.load(_FakePlugin(name="dup"), container=container)

    with pytest.raises(PluginValidationException):
        loader.load(_FakePlugin(name="dup"), container=container)


def test_is_loaded_false_for_unknown_plugin() -> None:
    loader = PluginLoader()
    assert loader.is_loaded("does-not-exist") is False


def test_unload_removes_loaded_plugin() -> None:
    loader = PluginLoader()
    container = ServiceContainer()
    loader.load(_FakePlugin(name="removable"), container=container)

    loader.unload("removable")

    assert loader.is_loaded("removable") is False
    assert loader.list_loaded() == ()


def test_unload_unknown_plugin_raises() -> None:
    loader = PluginLoader()
    with pytest.raises(PluginValidationException):
        loader.unload("does-not-exist")


def test_plugin_default_metadata_derives_from_name_and_version() -> None:
    plugin = _FakePlugin(name="fake-plugin", version="2.0.0")

    metadata = plugin.metadata

    assert metadata == PluginMetadata(id="fake-plugin", name="fake-plugin", version="2.0.0")
    assert metadata.lifecycle is PluginLifecycleState.REGISTERED
    assert metadata.as_dict()["id"] == "fake-plugin"


def test_plugin_metadata_as_dict_is_serializable() -> None:
    metadata = PluginMetadata(
        id="demo",
        name="Demo Plugin",
        version="1.0.0",
        description="Un plugin de ejemplo",
        author="TEAF Team",
        license="MIT",
        dependencies=("core",),
        capabilities=("demo.cap",),
        priority=10,
        tags=("demo",),
        compatible_runtime=">=0.4.0",
        lifecycle=PluginLifecycleState.LOADED,
        experimental=True,
    )

    payload = metadata.as_dict()

    assert payload["id"] == "demo"
    assert payload["dependencies"] == ["core"]
    assert payload["capabilities"] == ["demo.cap"]
    assert payload["priority"] == 10
    assert payload["compatibleRuntime"] == ">=0.4.0"
    assert payload["lifecycle"] == "loaded"
    assert payload["experimental"] is True
