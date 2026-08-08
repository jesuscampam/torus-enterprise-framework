"""``RuntimeDiagnostics`` — fotografía operativa detallada del Runtime.

Complementa (no sustituye) a ``RuntimeMetadata`` (``backend/runtime/runtime.py``,
Sprint 2.3, consumida por ``GET /info``): ``RuntimeMetadata`` es el resumen
mínimo de arranque; ``RuntimeDiagnostics`` es la vista extendida de
Sprint 2.4, consumida por ``GET /runtime/info`` y por ``Runtime.diagnostics()``.

``memory_rss_bytes``/``cpu_time_seconds`` son reales desde Sprint 2.8 (ver
ADR-008) — antes, ``memory_placeholder``/``cpu_placeholder`` eran literales
explícitos ``"not-implemented"``. Se calculan en el propio
``Runtime.diagnostics()`` (``runtime.py``) delegando en
``teaf._internal.runtime.process_metrics`` (Windows Compatibility Patch,
v0.10.1-alpha), que resuelve la implementación real por plataforma —
``resource.getrusage()`` en POSIX, ``ctypes``/``os.times()`` en Windows—,
siempre de la librería estándar, sin dependencia nueva. Que sigan siendo
``int | None``/``float | None`` es justamente lo que permite que la cifra
falte en una plataforma sin que el resto del diagnóstico se vea afectado.
``teaf._internal.observability.diagnostics`` (Sprint 2.8) construye el
``DiagnosticReport`` agregado — envuelve esta misma clase (``as_dict()``)
junto al ``HealthReport`` de ``CompositeHealthChecker``, sin recalcular
ninguno de sus campos.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RuntimeDiagnostics:
    """Diagnóstico operativo del Runtime en el momento de la consulta."""

    runtime_id: str
    startup_time: datetime | None
    running_time_seconds: float
    registered_modules: int
    registered_services: int
    registered_capabilities: int
    registered_plugins: int
    registered_features: int
    framework_version: str
    python_version: str
    configuration_summary: Mapping[str, object] = field(default_factory=dict)
    dependency_graph_summary: Mapping[str, object] = field(default_factory=dict)
    container_statistics: Mapping[str, object] = field(default_factory=dict)
    memory_rss_bytes: int | None = None
    cpu_time_seconds: float | None = None

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este diagnóstico."""
        return {
            "runtimeId": self.runtime_id,
            "startupTime": self.startup_time.isoformat() if self.startup_time else None,
            "runningTimeSeconds": self.running_time_seconds,
            "registeredModules": self.registered_modules,
            "registeredServices": self.registered_services,
            "registeredCapabilities": self.registered_capabilities,
            "registeredPlugins": self.registered_plugins,
            "registeredFeatures": self.registered_features,
            "frameworkVersion": self.framework_version,
            "pythonVersion": self.python_version,
            "configurationSummary": dict(self.configuration_summary),
            "dependencyGraphSummary": dict(self.dependency_graph_summary),
            "containerStatistics": dict(self.container_statistics),
            "memoryRssBytes": self.memory_rss_bytes,
            "cpuTimeSeconds": self.cpu_time_seconds,
        }
