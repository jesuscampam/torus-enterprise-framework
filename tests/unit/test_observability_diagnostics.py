"""Pruebas unitarias de teaf/_internal/observability/diagnostics.py (build_diagnostic_report)."""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.modules.observability.configuration import ObservabilityConfiguration
from teaf._internal.modules.observability.module import ObservabilityModule
from teaf._internal.observability.diagnostics import build_diagnostic_report
from teaf._internal.runtime.event_bus import EventBus
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.context import ModuleContext


@pytest.fixture
def runtime() -> Runtime:
    rt = Runtime(registry=ModuleRegistry(), framework_version="0.8.0-alpha")
    asyncio.run(rt.startup())
    return rt


def test_build_diagnostic_report_without_modules_wraps_runtime_diagnostics(
    runtime: Runtime,
) -> None:
    report = build_diagnostic_report(runtime)
    assert report.runtime["runtimeId"] == runtime.diagnostics().runtime_id
    assert report.health.checks == {}


def test_build_diagnostic_report_includes_the_health_of_bootstrapped_modules(
    runtime: Runtime,
) -> None:
    module = ObservabilityModule(ObservabilityConfiguration())
    context = ModuleContext(runtime=runtime, module_id="observability")
    asyncio.run(module.bootstrap(context))

    report = build_diagnostic_report(runtime, [module])
    assert "observability.observability.ping" in report.health.checks


def test_build_diagnostic_report_publishes_diagnostic_generated_when_given_an_event_bus(
    runtime: Runtime,
) -> None:
    event_bus = EventBus()
    build_diagnostic_report(runtime, [], event_bus=event_bus)
    assert any(event.name == "diagnostic.generated" for event in event_bus.history())


def test_build_diagnostic_report_does_not_publish_without_an_event_bus(runtime: Runtime) -> None:
    # Simplemente no debe lanzar — no hay ningún EventBus al que verificarle nada.
    build_diagnostic_report(runtime, [])
