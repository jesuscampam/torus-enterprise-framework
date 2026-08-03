"""``RuntimeSelfDescription`` — el framework describiéndose a sí mismo.

Consumida por ``GET /runtime/self`` y por ``Runtime.self_description()``:
responde, de una sola vez, qué es TEAF, qué versión corre, qué módulos,
servicios, capacidades, plugins y feature flags tiene registrados, y qué
subsistemas soporta — sin datos simulados, todo leído del Runtime en el
momento de la consulta (ver Sprint 2.4, ítem 8, "Toda la información deberá
provenir del Runtime").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeSelfDescription:
    """Respuesta a la pregunta "¿qué eres y qué puedes hacer?"."""

    framework: str
    version: str
    runtime_state: str
    modules: tuple[str, ...]
    services: tuple[str, ...]
    capabilities: tuple[str, ...]
    plugins: tuple[str, ...]
    feature_flags: tuple[str, ...]
    supports_ai: bool
    supports_mcp: bool
    supports_scheduler: bool
    supports_database: bool
    supports_storage: bool
    supports_notifications: bool
    supported_runtime_version: str
    supported_python_version: str

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta autodescripción."""
        return {
            "framework": self.framework,
            "version": self.version,
            "runtimeState": self.runtime_state,
            "modules": list(self.modules),
            "services": list(self.services),
            "capabilities": list(self.capabilities),
            "plugins": list(self.plugins),
            "featureFlags": list(self.feature_flags),
            "supports": {
                "ai": self.supports_ai,
                "mcp": self.supports_mcp,
                "scheduler": self.supports_scheduler,
                "database": self.supports_database,
                "storage": self.supports_storage,
                "notifications": self.supports_notifications,
            },
            "supportedRuntimeVersion": self.supported_runtime_version,
            "supportedPythonVersion": self.supported_python_version,
        }
