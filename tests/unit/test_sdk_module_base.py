"""Pruebas unitarias de backend/sdk/module_base.py (ModuleBase) y backend/sdk/context.py."""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.exceptions import (
    ModuleCompatibilityException,
    ModuleLifecycleException,
    ModuleRegistrationException,
    ModuleValidationException,
)
from teaf._internal.sdk.lifecycle import ModuleLifecycleState
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


class _Greeter:
    pass


def _running_runtime(*, framework_version: str = "0.5.0-alpha") -> Runtime:
    runtime = Runtime(registry=ModuleRegistry(), framework_version=framework_version)
    asyncio.run(runtime.startup())
    return runtime


class _DemoModule(ModuleBase):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="demo", name="demo", display_name="Demo")
            .with_version("0.1.0")
            .add_service(_Greeter, lambda c: _Greeter())
            .add_capability(id="demo.greet", name="demo-greet")
            .build()
        )

    def initialize(self, context: ModuleContext) -> None:
        self.calls.append("initialize")

    def configure(self, context: ModuleContext) -> None:
        self.calls.append("configure")

    def register(self, context: ModuleContext) -> None:
        self.calls.append("register")

    async def start(self, context: ModuleContext) -> None:
        self.calls.append("start")

    async def ready(self, context: ModuleContext) -> None:
        self.calls.append("ready")
        context.logger.info("demo_ready")

    def stop(self, context: ModuleContext) -> None:
        self.calls.append("stop")

    def dispose(self, context: ModuleContext) -> None:
        self.calls.append("dispose")


def test_module_context_exposes_runtime_shortcuts() -> None:
    runtime = _running_runtime()
    context = ModuleContext(runtime=runtime, module_id="demo", configuration={"level": "info"})

    assert context.container is runtime.container
    assert context.capabilities is runtime.capability_registry
    assert context.features is runtime.feature_manager
    assert context.events is runtime.event_bus
    assert context.logger.name == "teaf.module.demo"
    assert context.configuration == {"level": "info"}


def test_bootstrap_runs_hooks_in_order_mixing_sync_and_async() -> None:
    runtime = _running_runtime()
    module = _DemoModule()
    context = ModuleContext(runtime=runtime, module_id="demo")

    asyncio.run(module.bootstrap(context))

    assert module.calls == ["initialize", "configure", "register", "start", "ready"]


def test_bootstrap_registers_module_in_core_registry() -> None:
    runtime = _running_runtime()
    module = _DemoModule()
    context = ModuleContext(runtime=runtime, module_id="demo")

    asyncio.run(module.bootstrap(context))

    descriptor = runtime.modules[0]
    assert descriptor.name == "demo"
    assert descriptor.version == "0.1.0"
    assert descriptor.capabilities == ("demo.greet",)


def test_bootstrap_binds_declared_services_and_capabilities() -> None:
    runtime = _running_runtime()
    module = _DemoModule()
    context = ModuleContext(runtime=runtime, module_id="demo")

    asyncio.run(module.bootstrap(context))

    assert runtime.container.is_registered(_Greeter) is True
    assert runtime.capability_registry.exists("demo.greet") is True


def test_bootstrap_advances_lifecycle_to_ready() -> None:
    runtime = _running_runtime()
    module = _DemoModule()
    context = ModuleContext(runtime=runtime, module_id="demo")

    asyncio.run(module.bootstrap(context))

    assert module.lifecycle.state is ModuleLifecycleState.READY


def test_shutdown_runs_stop_then_dispose() -> None:
    runtime = _running_runtime()
    module = _DemoModule()
    context = ModuleContext(runtime=runtime, module_id="demo")
    asyncio.run(module.bootstrap(context))

    asyncio.run(module.shutdown(context))

    assert module.calls[-2:] == ["stop", "dispose"]
    assert module.lifecycle.state is ModuleLifecycleState.DISPOSED


def test_bootstrap_raises_on_invalid_manifest() -> None:
    class _BadModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return ModuleBuilder(id="Bad Id!", name="").build()

    runtime = _running_runtime()
    module = _BadModule()
    context = ModuleContext(runtime=runtime, module_id="bad")

    with pytest.raises(ModuleValidationException):
        asyncio.run(module.bootstrap(context))
    assert module.lifecycle.state is ModuleLifecycleState.FAILED


def test_bootstrap_raises_on_runtime_incompatibility() -> None:
    class _IncompatibleModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return (
                ModuleBuilder(id="incompat", name="incompat")
                .with_runtime_compatibility(">=99.0")
                .build()
            )

    runtime = _running_runtime()
    module = _IncompatibleModule()
    context = ModuleContext(runtime=runtime, module_id="incompat")

    with pytest.raises(ModuleCompatibilityException):
        asyncio.run(module.bootstrap(context))
    assert module.lifecycle.state is ModuleLifecycleState.FAILED


def test_bootstrap_raises_on_sdk_incompatibility() -> None:
    class _IncompatibleModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return (
                ModuleBuilder(id="incompat", name="incompat")
                .with_sdk_compatibility(">=99.0")
                .build()
            )

    runtime = _running_runtime()
    module = _IncompatibleModule()
    context = ModuleContext(runtime=runtime, module_id="incompat")

    with pytest.raises(ModuleCompatibilityException):
        asyncio.run(module.bootstrap(context))


def test_bootstrap_raises_on_duplicate_registration() -> None:
    class _DupModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return ModuleBuilder(id="dup", name="dup").build()

    runtime = _running_runtime()
    context = ModuleContext(runtime=runtime, module_id="dup")
    asyncio.run(_DupModule().bootstrap(context))

    with pytest.raises(ModuleRegistrationException):
        asyncio.run(_DupModule().bootstrap(context))


def test_bootstrap_wraps_hook_failure_in_lifecycle_exception() -> None:
    class _FailingModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return ModuleBuilder(id="failing", name="failing").build()

        def start(self, context: ModuleContext) -> None:
            raise RuntimeError("boom")

    runtime = _running_runtime()
    module = _FailingModule()
    context = ModuleContext(runtime=runtime, module_id="failing")

    with pytest.raises(ModuleLifecycleException, match="boom"):
        asyncio.run(module.bootstrap(context))
    assert module.lifecycle.state is ModuleLifecycleState.FAILED


def test_default_hooks_are_no_ops() -> None:
    class _MinimalModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return ModuleBuilder(id="minimal", name="minimal").build()

    runtime = _running_runtime()
    module = _MinimalModule()
    context = ModuleContext(runtime=runtime, module_id="minimal")

    asyncio.run(module.bootstrap(context))
    asyncio.run(module.shutdown(context))

    assert module.lifecycle.state is ModuleLifecycleState.DISPOSED


def test_runtime_compatibility_wildcard_always_satisfied() -> None:
    class _WildcardModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return (
                ModuleBuilder(id="wildcard", name="wildcard")
                .with_runtime_compatibility("*")
                .build()
            )

    runtime = _running_runtime(framework_version="0.0.1")
    module = _WildcardModule()
    context = ModuleContext(runtime=runtime, module_id="wildcard")

    asyncio.run(module.bootstrap(context))  # no debe lanzar

    assert module.lifecycle.state is ModuleLifecycleState.READY
