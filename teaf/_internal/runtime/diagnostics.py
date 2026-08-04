"""``RuntimeDiagnostics`` — fotografía operativa detallada del Runtime.

Complementa (no sustituye) a ``RuntimeMetadata`` (``backend/runtime/runtime.py``,
Sprint 2.3, consumida por ``GET /info``): ``RuntimeMetadata`` es el resumen
mínimo de arranque; ``RuntimeDiagnostics`` es la vista extendida de
Sprint 2.4, consumida por ``GET /runtime/info`` y por ``Runtime.diagnostics()``.

Sin métricas reales de memoria/CPU en este Sprint (ver "NO IMPLEMENTAR":
sin OpenTelemetry real) — ``memory_placeholder``/``cpu_placeholder`` son
literales explícitos que documentan la ausencia de la métrica, listos para
que un Sprint futuro los reemplace por valores reales sin cambiar la forma
de ``RuntimeDiagnostics``.
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
    memory_placeholder: str = "not-implemented"
    cpu_placeholder: str = "not-implemented"

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
            "memoryPlaceholder": self.memory_placeholder,
            "cpuPlaceholder": self.cpu_placeholder,
        }
