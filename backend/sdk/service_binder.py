"""``ServiceBinder`` — registra automáticamente los servicios declarados por un módulo.

Traduce cada ``ModuleService`` (declaración, ``service.py``) en una llamada
real a ``Runtime.register_service`` — el autor del módulo nunca escribe
``container.register_singleton(...)`` a mano (ver Sprint 2.5, ítem 7).
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.runtime.container import ServiceMetadata
from backend.runtime.runtime import Runtime
from backend.sdk.service import ModuleService


class ServiceBinder:
    """Registra ``ModuleService`` contra el ``ServiceContainer`` de un ``Runtime``."""

    def bind(self, services: Iterable[ModuleService], *, runtime: Runtime, module_id: str) -> None:
        """Registra cada servicio de ``services``, con metadata derivada de ``module_id``."""
        for service in services:
            metadata = ServiceMetadata(
                service_id=f"{module_id}.{service.contract.__name__}",
                name=service.contract.__name__,
                lifetime=service.lifetime,
                module=module_id,
                description=service.description,
                tags=service.tags,
                capabilities=service.capabilities,
            )
            runtime.register_service(
                service.contract,
                service.factory,
                lifetime=service.lifetime,
                metadata=metadata,
            )
