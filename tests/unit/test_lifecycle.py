"""Pruebas unitarias de backend/runtime/lifecycle.py y pipeline.py."""

from __future__ import annotations

import asyncio

import pytest
from backend.runtime.exceptions import LifecycleException
from backend.runtime.lifecycle import LifecycleManager, LifecycleStage
from backend.runtime.pipeline import Pipeline, ShutdownPipeline, StartupPipeline


def test_lifecycle_manager_starts_without_current_stage() -> None:
    manager = LifecycleManager()
    assert manager.current_stage is None


def test_run_stage_executes_hooks_in_registration_order() -> None:
    manager = LifecycleManager()
    calls: list[str] = []
    manager.on(LifecycleStage.STARTUP, lambda: calls.append("first"))
    manager.on(LifecycleStage.STARTUP, lambda: calls.append("second"))

    asyncio.run(manager.run_stage(LifecycleStage.STARTUP))

    assert calls == ["first", "second"]
    assert manager.current_stage == LifecycleStage.STARTUP


def test_run_stage_supports_async_hooks() -> None:
    manager = LifecycleManager()
    calls: list[str] = []

    async def async_hook() -> None:
        calls.append("async")

    manager.on(LifecycleStage.BOOTSTRAP, async_hook)
    asyncio.run(manager.run_stage(LifecycleStage.BOOTSTRAP))

    assert calls == ["async"]


def test_run_stage_wraps_hook_failure_in_lifecycle_exception() -> None:
    manager = LifecycleManager()

    def failing_hook() -> None:
        raise RuntimeError("boom")

    manager.on(LifecycleStage.SHUTDOWN, failing_hook)

    with pytest.raises(LifecycleException):
        asyncio.run(manager.run_stage(LifecycleStage.SHUTDOWN))


def test_startup_pipeline_runs_steps_fifo() -> None:
    pipeline = StartupPipeline()
    order: list[str] = []
    pipeline.add_step("first", lambda: order.append("first"))
    pipeline.add_step("second", lambda: order.append("second"))

    asyncio.run(pipeline.run())

    assert order == ["first", "second"]


def test_shutdown_pipeline_runs_steps_lifo() -> None:
    pipeline = ShutdownPipeline()
    order: list[str] = []
    pipeline.add_step("acquired-first", lambda: order.append("acquired-first"))
    pipeline.add_step("acquired-second", lambda: order.append("acquired-second"))

    asyncio.run(pipeline.run())

    assert order == ["acquired-second", "acquired-first"]


def test_pipeline_step_failure_raises_lifecycle_exception() -> None:
    pipeline = Pipeline(name="custom")

    def failing_step() -> None:
        raise ValueError("no se pudo")

    pipeline.add_step("failing", failing_step)

    with pytest.raises(LifecycleException, match="custom"):
        asyncio.run(pipeline.run())


def test_pipeline_steps_are_exposed_in_run_order() -> None:
    startup = StartupPipeline()
    startup.add_step("a", lambda: None)
    startup.add_step("b", lambda: None)
    assert [step.name for step in startup.steps()] == ["a", "b"]

    shutdown = ShutdownPipeline()
    shutdown.add_step("a", lambda: None)
    shutdown.add_step("b", lambda: None)
    assert [step.name for step in shutdown.steps()] == ["b", "a"]
