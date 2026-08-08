"""Health Checks — CompositeHealthChecker agregando el ModuleHealth de varios módulos.

``Application`` ya conecta ``/health``/``/ready`` a un
``CompositeHealthChecker`` real (Sprint 2.8, ADR-008) que evalúa el
``ModuleHealth`` de cada módulo bootstrapeado — este ejemplo no construye
el checker a mano, solo registra dos módulos con estados de salud
distintos y observa cómo ``/health``/``/ready`` reflejan el peor estado.

Ejecutar:

    python examples/health-checks/main.py
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from teaf import Application, CapabilityCategory, Health, Module, ModuleBuilder, ModuleManifest


class PaymentsGatewayModule(Module):
    """Simula un módulo sano — su dependencia externa responde con normalidad."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="payments", name="payments", display_name="Payments Gateway")
            .with_version("1.0.0")
            .add_capability(
                id="payments.charge",
                name="payments-charge",
                category=CapabilityCategory.INTEGRATION,
            )
            .add_healthcheck(name="payments.ping", check=lambda: Health.HEALTHY)
            .build()
        )


class ShippingProviderModule(Module):
    """Simula un módulo degradado — su dependencia externa está lenta pero responde."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="shipping", name="shipping", display_name="Shipping Provider")
            .with_version("1.0.0")
            .add_capability(
                id="shipping.quote",
                name="shipping-quote",
                category=CapabilityCategory.INTEGRATION,
            )
            .add_healthcheck(name="shipping.ping", check=lambda: Health.DEGRADED)
            .build()
        )


app = Application(modules=[PaymentsGatewayModule(), ShippingProviderModule()])

with TestClient(app.asgi) as client:
    health = client.get("/health").json()
    print("GET /health ->", health["status"])
    print("  módulos:", health["modules"])

    ready = client.get("/ready")
    print(f"GET /ready -> {ready.status_code}", ready.json())
