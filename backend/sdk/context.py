"""``ModuleContext`` — lo que recibe un módulo en cada hook de su ciclo de vida.

Envuelve el ``Runtime`` (Sprint 2.3) más la configuración resuelta para
este módulo y un logger con nombre — así un ``ModuleBase`` nunca necesita
importar ``backend/runtime/`` directamente ni construirse su propio logger:
todo llega a través del contexto (ver ``module_base.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from logging import Logger

from backend.core.logging import get_logger
from backend.runtime.capabilities.registry import CapabilityRegistry
from backend.runtime.container import ServiceContainer
from backend.runtime.event_bus import EventBus
from backend.runtime.features.manager import FeatureManager
from backend.runtime.runtime import Runtime


@dataclass(frozen=True, slots=True)
class ModuleContext:
    """Contexto de ejecución de un módulo, pasado a cada hook de ``ModuleBase``."""

    runtime: Runtime
    module_id: str
    configuration: Mapping[str, object] = field(default_factory=dict)

    @property
    def logger(self) -> Logger:
        """Logger con nombre ``teaf.module.<module_id>``."""
        return get_logger(f"teaf.module.{self.module_id}")

    @property
    def container(self) -> ServiceContainer:
        """Atajo a ``runtime.container``."""
        return self.runtime.container

    @property
    def capabilities(self) -> CapabilityRegistry:
        """Atajo a ``runtime.capability_registry``."""
        return self.runtime.capability_registry

    @property
    def features(self) -> FeatureManager:
        """Atajo a ``runtime.feature_manager``."""
        return self.runtime.feature_manager

    @property
    def events(self) -> EventBus:
        """Atajo a ``runtime.event_bus``."""
        return self.runtime.event_bus
