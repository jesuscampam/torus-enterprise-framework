"""Ruta de sistema ``/info``: identidad de la instancia, módulos y estado del Runtime.

Depende únicamente de ``backend/core/`` (``VersionInfo``, ``ModuleRegistry``)
— igual que ``health.py``, para no violar "Monitoring depende únicamente
de Core" (ver FRAMEWORK-BLUEPRINT.md, sección 11, regla 2). El estado del
Runtime (Sprint 2.3) se recibe como un ``Callable`` genérico, no como el
tipo ``Runtime`` en sí — así este módulo no necesita importar
``backend/runtime/`` para seguir mostrando información fresca en cada
petición (el estado cambia con el tiempo: bootstrapping → running).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.core.version import VersionInfo

#: Devuelve una fotografía serializable del estado del Runtime en el
#: momento de la llamada (ver ``Runtime.describe().as_dict()``).
RuntimeStateProvider = Callable[[], dict[str, object]]


def create_info_router(
    version_info: VersionInfo,
    registry: ModuleRegistry,
    runtime_state_provider: RuntimeStateProvider,
) -> APIRouter:
    """Construye el router de introspección de la instancia en ejecución."""
    router = APIRouter(tags=["system"])

    @router.get("/info")
    def info() -> dict[str, object]:
        """Versión, módulos y estado del Runtime, leídos en el momento de la petición."""
        return {
            "name": version_info.name,
            "version": version_info.version,
            "environment": version_info.environment,
            "buildDate": version_info.build_date or "unknown",
            "modules": [
                {"name": module.name, "version": module.version, "status": module.status.value}
                for module in registry.list_modules()
            ],
            **runtime_state_provider(),
        }

    return router
