"""Modelo de dominio de la plataforma de observabilidad (Sprint 2.8, ADR-008).

``SpanKind``/``SpanStatus`` son el vocabulario propio de TEAF para
``contracts/telemetry.py`` — el adaptador de tracing (``observability/tracing/``)
los traduce a/desde los equivalentes de OpenTelemetry en el borde, para que
ningún contrato de ``teaf.observability`` filtre tipos de ``opentelemetry.*``
directamente (misma razón por la que ``contracts/database.py`` no filtra
tipos de SQLAlchemy). ``HealthCheck``/``HealthReport`` reutilizan
``CapabilityHealth`` (Sprint 2.4) en vez de definir un vocabulario de salud
propio — mismo criterio que ``teaf._internal.sdk.health.ModuleHealth``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from teaf._internal.runtime.capabilities.enums import CapabilityHealth


class SpanKind(str, Enum):
    """El rol de un span dentro de una traza — vocabulario de OpenTelemetry."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """El resultado de la operación que representa un span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """Una verificación de salud nombrada — mismo patrón que ``ModuleHealth``.

    ``critical`` decide si esta verificación cuenta para el *readiness*
    agregado (``CompositeHealthChecker.overall()``) o es solo informativa
    (aparece en el desglose, pero un fallo no marca la instancia como "no
    lista").
    """

    name: str
    check: Callable[[], CapabilityHealth] | None
    description: str = ""
    critical: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "critical": self.critical}


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Resultado agregado de evaluar un conjunto de ``HealthCheck``."""

    overall: CapabilityHealth
    checks: Mapping[str, CapabilityHealth] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.overall.value,
            "checks": {name: health.value for name, health in self.checks.items()},
        }


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """Fotografía completa de observabilidad: runtime + salud + metadatos de proceso.

    Complementa (no sustituye) a ``RuntimeDiagnostics``
    (``teaf._internal.runtime.diagnostics``, Sprint 2.4) — la envuelve y le
    añade el ``HealthReport`` agregado y la marca de tiempo de la propia
    consulta, sin duplicar ninguno de sus campos.
    """

    generated_at: datetime
    runtime: Mapping[str, object]
    health: HealthReport

    def as_dict(self) -> dict[str, object]:
        return {
            "generatedAt": self.generated_at.isoformat(),
            "runtime": dict(self.runtime),
            "health": self.health.as_dict(),
        }
