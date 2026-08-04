"""Prueba de integración: ``ObservabilityModule`` contra un ``Runtime``/``Application`` reales.

Mismo criterio que ``test_security_module_bootstrap.py``/``test_database_module_bootstrap.py``:
demuestra que ``ObservabilityModule`` se registra, arranca y opera contra el
``Runtime`` real, y que su ``ModuleHealth`` alimenta de verdad
``/health``/``/ready`` (Sprint 2.8) vía ``CompositeHealthChecker`` —
cerrando la brecha "ningún endpoint invoca estas funciones todavía"
documentada en ``sdk/health.py``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from teaf import Application
from teaf._internal.modules.observability.configuration import ObservabilityConfiguration
from teaf._internal.modules.observability.module import ObservabilityModule
from teaf._internal.observability.middleware import ObservabilityMiddleware
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.sdk.lifecycle import ModuleLifecycleState


def test_observability_module_manifest_declares_expected_capabilities_and_services() -> None:
    module = ObservabilityModule(ObservabilityConfiguration(console_exporter_enabled=False))
    manifest = module.get_manifest()

    assert manifest.descriptor.id == "observability"
    capability_ids = {c.id for c in manifest.capabilities}
    assert capability_ids == {
        "observability",
        "observability.tracing",
        "observability.metrics",
        "observability.health",
    }
    assert len(manifest.services) == 2
    assert len(manifest.health_checks) == 1


def test_observability_module_bootstraps_via_application_and_reaches_ready() -> None:
    module = ObservabilityModule(ObservabilityConfiguration(console_exporter_enabled=False))
    app = Application(modules=[module])

    with TestClient(app.asgi) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert module.lifecycle.state is ModuleLifecycleState.READY
        assert any(m.name == "observability" for m in app.runtime.modules)
        assert app.runtime.capability_registry.exists("observability.tracing")


def test_observability_module_health_becomes_healthy_after_start() -> None:
    module = ObservabilityModule(ObservabilityConfiguration())
    app = Application(modules=[module])

    with TestClient(app.asgi):
        assert module.health.check() is CapabilityHealth.HEALTHY


def test_health_endpoint_reports_observability_module_breakdown() -> None:
    module = ObservabilityModule(ObservabilityConfiguration())
    app = Application(modules=[module])

    with TestClient(app.asgi) as client:
        response = client.get("/health")
        body = response.json()
        assert body["modules"]["checks"]["observability.observability.ping"] == "healthy"


def test_ready_endpoint_returns_503_when_a_critical_check_is_unhealthy() -> None:
    module = ObservabilityModule(ObservabilityConfiguration(console_exporter_enabled=False))
    app = Application(modules=[module])

    with TestClient(app.asgi) as client:
        # Sin ningún exportador configurado, ObservabilityHealth.refresh()
        # marca DEGRADED, no UNHEALTHY — forzamos UNHEALTHY directamente
        # para probar que /ready lo propaga como 503.
        module.health._last_known = CapabilityHealth.UNHEALTHY  # noqa: SLF001

        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"


def test_observability_middleware_wires_against_module_tracer_and_meter() -> None:
    module = ObservabilityModule(ObservabilityConfiguration(console_exporter_enabled=False))
    app = Application(modules=[module])
    app.asgi.add_middleware(ObservabilityMiddleware, tracer=module.tracer, meter=module.meter)

    with TestClient(app.asgi) as client:
        response = client.get("/health")
        assert response.status_code == 200
