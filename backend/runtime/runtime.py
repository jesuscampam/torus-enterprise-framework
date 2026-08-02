"""``Runtime`` — orquestador del Sprint 2.3: compone todas las piezas del Runtime.

Es al Runtime lo que ``backend/core/application.py`` es a la aplicación
FastAPI: un composition root local que ensambla ``ServiceContainer``,
``LifecycleManager``, ``StartupPipeline``/``ShutdownPipeline``, ``EventBus``,
``PluginLoader`` y ``ConfigurationPipeline`` en una única secuencia de
arranque/apagado coherente.

``Runtime`` solo depende de ``backend/core/`` (``ModuleRegistry`` y
excepciones) — nunca de ``backend/contracts/`` ni ``backend/providers/``,
para permanecer independiente de cualquier implementación concreta (ver
docs/runtime/RUNTIME.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.core.registry import ModuleRegistry
from backend.runtime.configuration_pipeline import ConfigurationPipeline
from backend.runtime.container import ServiceContainer
from backend.runtime.dependency_graph import DependencyGraph
from backend.runtime.discovery import ModuleDiscovery
from backend.runtime.event_bus import Event, EventBus
from backend.runtime.lifecycle import LifecycleManager, LifecycleStage
from backend.runtime.pipeline import ShutdownPipeline, StartupPipeline
from backend.runtime.plugin_loader import PluginLoader


class RuntimeState(str, Enum):
    """Estado de alto nivel del Runtime, independiente de la etapa de ``LifecycleManager``."""

    BOOTSTRAPPING = "bootstrapping"
    RUNNING = "running"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RuntimeMetadata:
    """Fotografía del estado del Runtime, expuesta vía ``GET /info``."""

    state: RuntimeState
    lifecycle_stage: LifecycleStage | None
    loaded_modules: tuple[str, ...]
    registered_capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta metadata."""
        return {
            "state": self.state.value,
            "lifecycleStage": self.lifecycle_stage.value if self.lifecycle_stage else None,
            "loadedModules": list(self.loaded_modules),
            "registeredCapabilities": list(self.registered_capabilities),
        }


class Runtime:
    """Compone y orquesta el ciclo de vida completo del Framework."""

    def __init__(self, *, registry: ModuleRegistry) -> None:
        self.container = ServiceContainer()
        self.lifecycle = LifecycleManager()
        self.startup_pipeline = StartupPipeline()
        self.shutdown_pipeline = ShutdownPipeline()
        self.event_bus = EventBus()
        self.plugin_loader = PluginLoader()
        self.configuration_pipeline = ConfigurationPipeline()

        self._registry = registry
        self._discovery = ModuleDiscovery(registry)
        self._state = RuntimeState.BOOTSTRAPPING

    @property
    def state(self) -> RuntimeState:
        """Estado actual del Runtime."""
        return self._state

    async def startup(self) -> None:
        """Arranca el Runtime: Bootstrap → valida config → verifica el grafo de
        dependencias → Startup (pipeline + hooks) → Running.
        """
        await self.lifecycle.run_stage(LifecycleStage.BOOTSTRAP)
        self.configuration_pipeline.validate_all()

        graph = DependencyGraph(self._discovery.discover())
        graph.topological_order()  # lanza CircularDependencyException si hay un ciclo

        await self.lifecycle.run_stage(LifecycleStage.STARTUP)
        await self.startup_pipeline.run()

        self._state = RuntimeState.RUNNING
        await self.lifecycle.run_stage(LifecycleStage.RUNNING)
        self.event_bus.publish(Event(name="framework.startup.completed"))

    async def shutdown(self) -> None:
        """Apaga el Runtime: Shutdown (pipeline en orden inverso + hooks) → Stopped."""
        await self.shutdown_pipeline.run()
        await self.lifecycle.run_stage(LifecycleStage.SHUTDOWN)

        self._state = RuntimeState.STOPPED
        await self.lifecycle.run_stage(LifecycleStage.STOPPED)
        self.event_bus.publish(Event(name="framework.shutdown.completed"))

    def describe(self) -> RuntimeMetadata:
        """Fotografía actual del estado del Runtime."""
        return RuntimeMetadata(
            state=self._state,
            lifecycle_stage=self.lifecycle.current_stage,
            loaded_modules=tuple(d.name for d in self._discovery.discover()),
            registered_capabilities=tuple(
                sorted(contract.__name__ for contract in self.container.registered_contracts())
            ),
        )
