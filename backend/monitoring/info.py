"""Ruta de sistema ``/info``: identidad de la instancia y módulos registrados.

Depende únicamente de ``backend/core/`` (``VersionInfo``, ``ModuleRegistry``)
— igual que ``health.py``, para no violar "Monitoring depende únicamente
de Core" (ver FRAMEWORK-BLUEPRINT.md, sección 11, regla 2).
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.core.registry import ModuleRegistry
from backend.core.version import VersionInfo


def create_info_router(version_info: VersionInfo, registry: ModuleRegistry) -> APIRouter:
    """Construye el router de introspección de la instancia en ejecución."""
    router = APIRouter(tags=["system"])

    @router.get("/info")
    def info() -> dict[str, object]:
        """Identidad de versión y estado de registro de cada módulo del framework."""
        return {
            "name": version_info.name,
            "version": version_info.version,
            "environment": version_info.environment,
            "buildDate": version_info.build_date or "unknown",
            "modules": [
                {"name": module.name, "version": module.version, "status": module.status.value}
                for module in registry.list_modules()
            ],
        }

    return router
