"""Runtime API — introspección HTTP del Runtime en ejecución (Sprint 2.4, ítem 7).

A diferencia de ``backend/monitoring/info.py`` (que depende únicamente de
``backend/core/`` y recibe el estado del Runtime como ``Callable`` genérico
para no importar ``backend/runtime/``), este router **vive dentro** de
``backend/runtime/`` y recibe la instancia real de ``Runtime`` — no hay
regla de capas que lo impida: es el propio Runtime describiéndose, no
Monitoring cruzando una frontera que no le corresponde.

Las funciones ``build_*_payload`` son el punto de reutilización con el
Developer API (``backend/developer/runtime_api.py``, ítem 13): ambos leen el
mismo ``Runtime`` y arman la misma forma de datos — el router solo añade la
capa HTTP encima, sin duplicar la lógica de ensamblado.

``configuration_provider`` es la única dependencia inyectada desde fuera:
el Runtime nunca importa ``backend/config/``, así que quien construye este
router (el composition root, ``backend/core/application.py``) es quien
aporta el resumen de configuración.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from fastapi import APIRouter

from teaf._internal.runtime.runtime import Runtime

#: Devuelve un resumen serializable de la configuración activa, aportado por
#: el composition root (único lugar con acceso a ``Settings``).
ConfigurationProvider = Callable[[], Mapping[str, object]]


def default_configuration_provider() -> Mapping[str, object]:
    """``ConfigurationProvider`` por defecto cuando nadie aporta configuración real."""
    return {}


def build_modules_payload(runtime: Runtime) -> list[dict[str, object]]:
    """Metadata de todos los módulos registrados."""
    return [module.as_dict() for module in runtime.modules]


def build_services_payload(runtime: Runtime) -> list[dict[str, object]]:
    """Metadata de todos los servicios registrados."""
    return [service.as_dict() for service in runtime.service_discovery.list()]


def build_plugins_payload(runtime: Runtime) -> list[dict[str, object]]:
    """Metadata de todos los plugins cargados."""
    return [plugin.metadata.as_dict() for plugin in runtime.plugin_loader.list_loaded()]


def build_capabilities_payload(runtime: Runtime) -> list[dict[str, object]]:
    """Metadata de todas las capacidades registradas."""
    return [capability.metadata.as_dict() for capability in runtime.capability_registry.list()]


def build_features_payload(runtime: Runtime) -> list[dict[str, object]]:
    """Metadata de todos los feature flags registrados."""
    return [flag.as_dict() for flag in runtime.feature_manager.list()]


def build_events_payload(runtime: Runtime, *, limit: int | None = None) -> list[dict[str, object]]:
    """Historial de eventos publicados en el ``EventBus`` del Runtime."""
    return [
        {"name": event.name, "payload": dict(event.payload)}
        for event in runtime.event_bus.history(limit=limit)
    ]


def build_dependencies_payload(runtime: Runtime) -> dict[str, object]:
    """Grafo de dependencias de módulos y árbol de dependencias de servicios."""
    diagnostics = runtime.diagnostics()
    return {
        "modules": diagnostics.dependency_graph_summary,
        "services": [
            runtime.service_discovery.dependency_tree(service.service_id)
            for service in runtime.service_discovery.list()
        ],
    }


def create_runtime_router(
    runtime: Runtime,
    *,
    configuration_provider: ConfigurationProvider = default_configuration_provider,
) -> APIRouter:
    """Construye el router de introspección del Runtime (``GET /runtime/*``).

    Toda la información expuesta se lee del ``Runtime`` en el momento de la
    petición — sin datos simulados ni caché.
    """
    router = APIRouter(prefix="/runtime", tags=["runtime"])

    @router.get("/info")
    def info() -> dict[str, object]:
        return runtime.diagnostics(configuration_summary=configuration_provider()).as_dict()

    @router.get("/modules")
    def modules() -> list[dict[str, object]]:
        return build_modules_payload(runtime)

    @router.get("/services")
    def services() -> list[dict[str, object]]:
        return build_services_payload(runtime)

    @router.get("/plugins")
    def plugins() -> list[dict[str, object]]:
        return build_plugins_payload(runtime)

    @router.get("/capabilities")
    def capabilities() -> list[dict[str, object]]:
        return build_capabilities_payload(runtime)

    @router.get("/features")
    def features() -> list[dict[str, object]]:
        return build_features_payload(runtime)

    @router.get("/events")
    def events(limit: int | None = None) -> list[dict[str, object]]:
        return build_events_payload(runtime, limit=limit)

    @router.get("/configuration")
    def configuration() -> dict[str, object]:
        return dict(configuration_provider())

    @router.get("/dependencies")
    def dependencies() -> dict[str, object]:
        return build_dependencies_payload(runtime)

    @router.get("/self")
    def self_() -> dict[str, object]:
        return runtime.self_description().as_dict()

    return router
