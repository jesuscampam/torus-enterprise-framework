"""Dependencias inyectables (``Depends()``) para los proveedores de infraestructura.

Punto único de acceso vía DI a Database/Security/Telemetry/Storage/AI (ver
FRAMEWORK-BLUEPRINT.md, Sprint 2.2, ítem 7). Ningún proveedor concreto
existe todavía:

- ``get_database_provider`` / ``get_storage_provider`` / ``get_ai_provider``
  lanzan ``InfrastructureException`` al invocarse — son un seam documentado,
  no una implementación.
- ``get_security_context`` / ``get_telemetry_context`` sí son utilizables
  hoy: devuelven un contexto por defecto seguro (anónimo / sin traza
  activa), re-exportados aquí desde sus módulos de origen para tener un
  único punto de importación por parte de futuros routers.
- ``get_module_registry`` lee ``request.app.state.module_registry`` — el
  registro se crea una vez por instancia de aplicación en
  ``backend/core/application.py``, no como singleton de proceso (ver la
  nota de diseño en ``backend/core/registry.py``).
"""

from __future__ import annotations

from fastapi import Request

from backend.contracts.ai import AIProvider
from backend.contracts.database import DatabaseProvider
from backend.contracts.storage import StorageProvider
from backend.core.exceptions import InfrastructureException
from backend.core.registry import ModuleRegistry
from backend.providers.security.security_context import get_security_context
from backend.providers.telemetry.telemetry_context import get_telemetry_context

__all__ = [
    "get_ai_provider",
    "get_database_provider",
    "get_module_registry",
    "get_security_context",
    "get_storage_provider",
    "get_telemetry_context",
]


def get_module_registry(request: Request) -> ModuleRegistry:
    """Devuelve el ``ModuleRegistry`` de la instancia de aplicación en curso."""
    registry: ModuleRegistry = request.app.state.module_registry
    return registry


def get_database_provider() -> DatabaseProvider:
    """Placeholder de DI: ningún ``DatabaseProvider`` concreto existe todavía."""
    raise InfrastructureException(
        "DatabaseProvider no implementado todavía (ver docs/roadmap/ROADMAP.md)."
    )


def get_storage_provider() -> StorageProvider:
    """Placeholder de DI: ningún ``StorageProvider`` concreto existe todavía."""
    raise InfrastructureException(
        "StorageProvider no implementado todavía (ver docs/roadmap/ROADMAP.md)."
    )


def get_ai_provider() -> AIProvider:
    """Placeholder de DI: ningún ``AIProvider`` concreto existe todavía."""
    raise InfrastructureException(
        "AIProvider no implementado todavía (ver docs/roadmap/ROADMAP.md)."
    )
