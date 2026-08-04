"""``build_diagnostic_report`` — ``DiagnosticReport`` agregado (Runtime + salud).

Envuelve ``Runtime.diagnostics()`` (``RuntimeDiagnostics`` — thread pool
implícito en ``container_statistics``, Event Bus/Service Container/módulos
cargados/capacidades/configuración ya cubiertos por sus campos existentes,
ver ``runtime/diagnostics.py``) y le añade el ``HealthReport`` agregado de
``CompositeHealthChecker`` (seguridad/base de datos/cualquier otro módulo
bootstrapeado aparecen ahí, vía su ``ModuleHealth`` declarado) — sin
duplicar ningún campo de ninguno de los dos.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from teaf._internal.observability.health.checker import CompositeHealthChecker
from teaf._internal.observability.models import DiagnosticReport
from teaf._internal.runtime.event_bus import Event, EventBus
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.module_base import ModuleBase


def build_diagnostic_report(
    runtime: Runtime, modules: Sequence[ModuleBase] = (), *, event_bus: EventBus | None = None
) -> DiagnosticReport:
    """Construye la fotografía completa de observabilidad en el momento de la llamada.

    Publica ``diagnostic.generated`` en ``event_bus`` si se pasa uno — igual
    que el resto de eventos de la plataforma de observabilidad
    (``ObservabilityMiddleware``), opcional para no forzar un ``EventBus``
    a quien solo quiere construir el reporte.
    """
    health_report = CompositeHealthChecker.from_modules(modules).check_all()
    report = DiagnosticReport(
        generated_at=datetime.now(UTC),
        runtime=runtime.diagnostics().as_dict(),
        health=health_report,
    )
    if event_bus is not None:
        event_bus.publish(
            Event(name="diagnostic.generated", payload={"status": health_report.overall.value})
        )
    return report
