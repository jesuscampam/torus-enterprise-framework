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

import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from teaf._internal.core.registry import ModuleDescriptor, ModuleRegistry
from teaf._internal.runtime.capabilities.metadata import Capability
from teaf._internal.runtime.capabilities.provider_registry import CapabilityProviderRegistry
from teaf._internal.runtime.capabilities.registry import CapabilityRegistry
from teaf._internal.runtime.configuration_pipeline import ConfigurationPipeline
from teaf._internal.runtime.container import Factory, Lifetime, ServiceContainer, ServiceMetadata
from teaf._internal.runtime.dependency_graph import DependencyGraph
from teaf._internal.runtime.diagnostics import RuntimeDiagnostics
from teaf._internal.runtime.discovery import ModuleDiscovery
from teaf._internal.runtime.event_bus import Event, EventBus
from teaf._internal.runtime.features.enums import FeatureStatus
from teaf._internal.runtime.features.flag import FeatureFlag
from teaf._internal.runtime.features.manager import FeatureManager
from teaf._internal.runtime.lifecycle import LifecycleManager, LifecycleStage
from teaf._internal.runtime.pipeline import ShutdownPipeline, StartupPipeline
from teaf._internal.runtime.plugin_loader import Plugin, PluginLoader
from teaf._internal.runtime.process_metrics import (
    current_cpu_time_seconds,
    current_memory_rss_bytes,
)
from teaf._internal.runtime.self_description import RuntimeSelfDescription
from teaf._internal.runtime.service_discovery import ServiceDiscovery


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

    def __init__(self, *, registry: ModuleRegistry, framework_version: str = "0.0.0") -> None:
        self.container = ServiceContainer()
        self.lifecycle = LifecycleManager()
        self.startup_pipeline = StartupPipeline()
        self.shutdown_pipeline = ShutdownPipeline()
        self.event_bus = EventBus()
        self.plugin_loader = PluginLoader()
        self.configuration_pipeline = ConfigurationPipeline()

        # Compuestos desde Sprint 2.4 (Platform Intelligence) — inventario de
        # capacidades, feature flags y descubrimiento de servicios, todos en
        # memoria (ver "NO IMPLEMENTAR": sin persistencia).
        self.capability_registry = CapabilityRegistry()
        self.feature_manager = FeatureManager()
        self._register_default_features()
        self.capability_provider_registry = CapabilityProviderRegistry()
        self.service_discovery = ServiceDiscovery(self.container)

        self._registry = registry
        self._discovery = ModuleDiscovery(registry)
        self._state = RuntimeState.BOOTSTRAPPING
        self._framework_version = framework_version
        self._runtime_id = str(uuid.uuid4())
        self._started_at: datetime | None = None

    def _register_default_features(self) -> None:
        """Registra feature flags del framework durante inicialización del Runtime.

        Sprint 3.3-disabled: EventBus se registra como disabled para inventariarlo
        en /runtime/features, pero su implementación real está pendiente para Sprint 3.3.
        """
        eventbus_flag = FeatureFlag(
            id="eventbus-distributed",
            name="Distributed Event Bus",
            description="EventBus distribuido sobre Redis Streams",
            status=FeatureStatus.DISABLED,
            tags=("platform", "async", "distributed"),
        )
        self.feature_manager.register(eventbus_flag)

    @property
    def state(self) -> RuntimeState:
        """Estado actual del Runtime."""
        return self._state

    @property
    def modules(self) -> tuple[ModuleDescriptor, ...]:
        """Todos los módulos registrados (atajo de ``ModuleRegistry.list_modules()``)."""
        return self._registry.list_modules()

    @property
    def framework_version(self) -> str:
        """Versión del framework con la que se construyó este ``Runtime``."""
        return self._framework_version

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
        self._started_at = datetime.now(UTC)
        await self.lifecycle.run_stage(LifecycleStage.RUNNING)
        # "framework.started" es el nombre de evento fijado en Sprint 2.4
        # (ítem 12); "framework.startup.completed" se conserva desde
        # Sprint 2.3 por compatibilidad — ambos se publican en el mismo punto.
        self.event_bus.publish(Event(name="framework.started"))
        self.event_bus.publish(Event(name="framework.startup.completed"))

    async def shutdown(self) -> None:
        """Apaga el Runtime: Shutdown (pipeline en orden inverso + hooks) → Stopped."""
        await self.shutdown_pipeline.run()
        await self.lifecycle.run_stage(LifecycleStage.SHUTDOWN)

        self._state = RuntimeState.STOPPED
        await self.lifecycle.run_stage(LifecycleStage.STOPPED)
        self.event_bus.publish(Event(name="framework.stopped"))
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

    # -- Wrappers de Sprint 2.4: cada uno delega en el registro/gestor
    # correspondiente y publica el evento asociado en ``event_bus`` (ítem 12).
    # Mantener el registro/gestor en sí libre de conocer el EventBus es lo
    # que permite reutilizarlos fuera de un Runtime (p. ej. en tests).

    def register_module(self, descriptor: ModuleDescriptor) -> None:
        """Da de alta ``descriptor`` en el ``ModuleRegistry`` y publica ``module.registered``."""
        self._registry.register(descriptor)
        self.event_bus.publish(Event(name="module.registered", payload={"name": descriptor.name}))

    def unregister_module(self, name: str) -> None:
        """Elimina el módulo ``name`` y publica ``module.unregistered``."""
        self._registry.unregister(name)
        self.event_bus.publish(Event(name="module.unregistered", payload={"name": name}))

    def register_service(
        self,
        contract: type,
        factory: Factory[object],
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        metadata: ServiceMetadata | None = None,
    ) -> None:
        """Registra ``factory`` de ``contract`` y publica ``service.registered``."""
        if lifetime is Lifetime.SINGLETON:
            self.container.register_singleton(contract, factory, metadata=metadata)
        elif lifetime is Lifetime.SCOPED:
            self.container.register_scoped(contract, factory, metadata=metadata)
        else:
            self.container.register_transient(contract, factory, metadata=metadata)
        self.event_bus.publish(
            Event(name="service.registered", payload={"contract": contract.__name__})
        )

    def remove_service(self, contract: type) -> None:
        """Elimina el proveedor de ``contract`` y publica ``service.removed``."""
        self.container.unregister(contract)
        self.event_bus.publish(
            Event(name="service.removed", payload={"contract": contract.__name__})
        )

    def resolve_service(self, contract: type) -> object:
        """Resuelve ``contract`` y publica ``service.resolved``."""
        instance: object = self.container.resolve(contract)
        self.event_bus.publish(
            Event(name="service.resolved", payload={"contract": contract.__name__})
        )
        return instance

    def register_capability(self, capability: Capability) -> None:
        """Da de alta ``capability`` y publica ``capability.registered``."""
        self.capability_registry.register(capability)
        self.event_bus.publish(
            Event(name="capability.registered", payload={"id": capability.metadata.id})
        )

    def remove_capability(self, capability_id: str) -> None:
        """Elimina la capacidad ``capability_id`` y publica ``capability.removed``."""
        self.capability_registry.unregister(capability_id)
        self.event_bus.publish(Event(name="capability.removed", payload={"id": capability_id}))

    def load_plugin(self, plugin: Plugin) -> None:
        """Carga ``plugin`` contra el ``ServiceContainer`` y publica ``plugin.loaded``."""
        self.plugin_loader.load(plugin, container=self.container)
        self.event_bus.publish(Event(name="plugin.loaded", payload={"name": plugin.name}))

    def unload_plugin(self, name: str) -> None:
        """Descarga el plugin ``name`` y publica ``plugin.unloaded``."""
        self.plugin_loader.unload(name)
        self.event_bus.publish(Event(name="plugin.unloaded", payload={"name": name}))

    def enable_feature(self, feature_id: str) -> None:
        """Activa el feature flag ``feature_id`` y publica ``feature.enabled``."""
        self.feature_manager.enable(feature_id)
        self.event_bus.publish(Event(name="feature.enabled", payload={"id": feature_id}))

    def disable_feature(self, feature_id: str) -> None:
        """Desactiva el feature flag ``feature_id`` y publica ``feature.disabled``."""
        self.feature_manager.disable(feature_id)
        self.event_bus.publish(Event(name="feature.disabled", payload={"id": feature_id}))

    def diagnostics(
        self, *, configuration_summary: Mapping[str, object] | None = None
    ) -> RuntimeDiagnostics:
        """Diagnóstico operativo extendido del Runtime (ver ``GET /runtime/info``).

        ``configuration_summary`` lo aporta el composition root
        (``backend/core/application.py``, único lugar con acceso a
        ``Settings``) — el Runtime nunca importa ``backend/config/``.
        """
        modules = self._discovery.discover()
        now = datetime.now(UTC)
        running_time_seconds = (now - self._started_at).total_seconds() if self._started_at else 0.0
        return RuntimeDiagnostics(
            runtime_id=self._runtime_id,
            startup_time=self._started_at,
            running_time_seconds=running_time_seconds,
            registered_modules=len(modules),
            registered_services=len(self.container.describe_services()),
            registered_capabilities=len(self.capability_registry.list()),
            registered_plugins=len(self.plugin_loader.list_loaded()),
            registered_features=len(self.feature_manager.list()),
            framework_version=self._framework_version,
            python_version=sys.version,
            configuration_summary=configuration_summary or {},
            dependency_graph_summary={
                "nodes": len(modules),
                "edges": sum(len(m.dependencies) for m in modules),
            },
            container_statistics={
                "registeredContracts": len(self.container.registered_contracts()),
            },
            memory_rss_bytes=self._current_memory_rss_bytes(),
            cpu_time_seconds=self._current_cpu_time_seconds(),
        )

    @staticmethod
    def _current_memory_rss_bytes() -> int | None:
        """Memoria residente del proceso. Ver ``process_metrics.py`` — la
        implementación difiere por plataforma; ``None`` si no se puede
        obtener, nunca una excepción."""
        return current_memory_rss_bytes()

    @staticmethod
    def _current_cpu_time_seconds() -> float | None:
        """Tiempo de CPU acumulado del proceso (usuario + sistema). Ver
        ``process_metrics.py``."""
        return current_cpu_time_seconds()

    def self_description(self) -> RuntimeSelfDescription:
        """El Runtime describiéndose a sí mismo (ver ``GET /runtime/self``)."""
        return RuntimeSelfDescription(
            framework="TEAF",
            version=self._framework_version,
            runtime_state=self._state.value,
            modules=tuple(d.name for d in self.modules),
            services=tuple(s.service_id for s in self.container.describe_services()),
            capabilities=tuple(c.metadata.id for c in self.capability_registry.list()),
            plugins=tuple(p.name for p in self.plugin_loader.list_loaded()),
            feature_flags=tuple(f.id for f in self.feature_manager.list()),
            supports_ai=self._registry.get("ai") is not None,
            supports_mcp=self._registry.get("mcp") is not None,
            supports_scheduler=self._registry.get("scheduler") is not None,
            supports_database=self._registry.get("database") is not None,
            supports_storage=self._registry.get("storage") is not None,
            supports_notifications=self._registry.get("notification") is not None,
            supported_runtime_version=self._framework_version,
            supported_python_version=sys.version,
        )
