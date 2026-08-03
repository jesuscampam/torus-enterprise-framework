"""``ModuleService`` — declaración de un servicio que un módulo registra en el ``ServiceContainer``.

``ServiceBinder`` (``service_binder.py``) traduce cada ``ModuleService`` en
una llamada real a ``Runtime.register_service`` — el autor del módulo nunca
llama directamente a ``ServiceContainer.register_singleton``/``_scoped``/``_transient``.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.runtime.container import Factory, Lifetime


@dataclass(frozen=True, slots=True)
class ModuleService:
    """Un servicio que un módulo declara y que el SDK registra automáticamente."""

    contract: type
    factory: Factory[object]
    lifetime: Lifetime = Lifetime.SINGLETON
    description: str = ""
    tags: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta declaración (sin la ``factory``)."""
        return {
            "contract": self.contract.__name__,
            "lifetime": self.lifetime.value,
            "description": self.description,
            "tags": list(self.tags),
            "capabilities": list(self.capabilities),
        }
