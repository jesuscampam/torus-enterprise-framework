"""Pruebas unitarias de backend/runtime/runtime.py (Runtime, orquestador)."""

from __future__ import annotations

import asyncio

import pytest
from backend.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from backend.runtime.event_bus import Event
from backend.runtime.exceptions import CircularDependencyException
from backend.runtime.lifecycle import LifecycleStage
from backend.runtime.runtime import Runtime, RuntimeState


def _registry(*descriptors: ModuleDescriptor) -> ModuleRegistry:
    registry = ModuleRegistry()
    for descriptor in descriptors:
        registry.register(descriptor)
    return registry


def test_runtime_starts_in_bootstrapping_state() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    assert runtime.state is RuntimeState.BOOTSTRAPPING
    assert runtime.lifecycle.current_stage is None


def test_startup_advances_state_and_lifecycle_to_running() -> None:
    runtime = Runtime(registry=ModuleRegistry())

    asyncio.run(runtime.startup())

    assert runtime.state is RuntimeState.RUNNING
    assert runtime.lifecycle.current_stage is LifecycleStage.RUNNING


def test_shutdown_advances_state_to_stopped() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    asyncio.run(runtime.startup())

    asyncio.run(runtime.shutdown())

    assert runtime.state is RuntimeState.STOPPED
    assert runtime.lifecycle.current_stage is LifecycleStage.STOPPED


def test_startup_runs_startup_pipeline_steps() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    calls: list[str] = []
    runtime.startup_pipeline.add_step("init", lambda: calls.append("init"))

    asyncio.run(runtime.startup())

    assert calls == ["init"]


def test_shutdown_runs_shutdown_pipeline_steps() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    calls: list[str] = []
    runtime.shutdown_pipeline.add_step("release", lambda: calls.append("release"))
    asyncio.run(runtime.startup())

    asyncio.run(runtime.shutdown())

    assert calls == ["release"]


def test_startup_validates_configuration_pipeline_before_running() -> None:
    runtime = Runtime(registry=ModuleRegistry())

    def bad_validator() -> None:
        raise ValueError("config inválida")

    runtime.configuration_pipeline.register("fake-module", bad_validator)

    with pytest.raises(Exception):  # noqa: B017 — se re-lanza como ConfigurationException
        asyncio.run(runtime.startup())

    assert runtime.state is RuntimeState.BOOTSTRAPPING  # nunca llegó a RUNNING


def test_startup_detects_circular_dependency_between_modules() -> None:
    registry = _registry(
        ModuleDescriptor(
            name="a", version="1", status=ModuleStatus.CONTRACTS_ONLY, dependencies=("b",)
        ),
        ModuleDescriptor(
            name="b", version="1", status=ModuleStatus.CONTRACTS_ONLY, dependencies=("a",)
        ),
    )
    runtime = Runtime(registry=registry)

    with pytest.raises(CircularDependencyException):
        asyncio.run(runtime.startup())


def test_startup_publishes_completion_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received: list[Event] = []
    runtime.event_bus.subscribe("framework.startup.completed", received.append)

    asyncio.run(runtime.startup())

    assert len(received) == 1


def test_shutdown_publishes_completion_event() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    received: list[Event] = []
    runtime.event_bus.subscribe("framework.shutdown.completed", received.append)
    asyncio.run(runtime.startup())

    asyncio.run(runtime.shutdown())

    assert len(received) == 1


def test_describe_reflects_loaded_modules_and_capabilities() -> None:
    registry = _registry(
        ModuleDescriptor(name="database", version="1", status=ModuleStatus.CONTRACTS_ONLY),
    )
    runtime = Runtime(registry=registry)

    class _Contract:
        pass

    runtime.container.register_transient(_Contract, lambda _c: _Contract())

    metadata = runtime.describe()

    assert metadata.loaded_modules == ("database",)
    assert metadata.registered_capabilities == ("_Contract",)
    assert metadata.state is RuntimeState.BOOTSTRAPPING


def test_describe_as_dict_is_json_serializable_shape() -> None:
    runtime = Runtime(registry=ModuleRegistry())
    asyncio.run(runtime.startup())

    payload = runtime.describe().as_dict()

    assert payload == {
        "state": "running",
        "lifecycleStage": "running",
        "loadedModules": [],
        "registeredCapabilities": [],
    }
