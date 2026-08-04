"""``CapabilityRegistry`` — inventario en tiempo de ejecución de capacidades.

Mismo espíritu que ``backend/core/registry.py`` (``ModuleRegistry``): un
registro en memoria, sin persistencia, consultado por la Runtime API
(``GET /runtime/capabilities``) y por ``CapabilityProviderRegistry`` (ver
``provider_registry.py``) para la futura integración con MCP.
"""

from __future__ import annotations

from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.capabilities.metadata import Capability
from teaf._internal.runtime.exceptions import (
    CapabilityAlreadyRegisteredException,
    CapabilityNotFoundException,
)


class CapabilityRegistry:
    """Registro central de capacidades del framework."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """Da de alta ``capability``.

        Raises:
            CapabilityAlreadyRegisteredException: si ya existe una capacidad
                con el mismo ``id``.
        """
        capability_id = capability.metadata.id
        if capability_id in self._capabilities:
            raise CapabilityAlreadyRegisteredException(
                f"La capacidad '{capability_id}' ya está registrada."
            )
        self._capabilities[capability_id] = capability

    def unregister(self, capability_id: str) -> None:
        """Elimina la capacidad ``capability_id``.

        Raises:
            CapabilityNotFoundException: si no existe.
        """
        if capability_id not in self._capabilities:
            raise CapabilityNotFoundException(f"La capacidad '{capability_id}' no existe.")
        del self._capabilities[capability_id]

    def find(self, capability_id: str) -> Capability | None:
        """Devuelve la capacidad ``capability_id``, o ``None`` si no existe."""
        return self._capabilities.get(capability_id)

    def exists(self, capability_id: str) -> bool:
        """``True`` si ``capability_id`` está registrada."""
        return capability_id in self._capabilities

    def list(self, *, category: CapabilityCategory | None = None) -> tuple[Capability, ...]:
        """Todas las capacidades registradas, opcionalmente filtradas por ``category``."""
        values = tuple(self._capabilities.values())
        if category is None:
            return values
        return tuple(c for c in values if c.metadata.category is category)

    def search(self, query: str) -> tuple[Capability, ...]:
        """Búsqueda simple por subcadena en ``id``, ``name``, ``display_name`` o ``tags``."""
        query_lower = query.lower()
        return tuple(
            capability
            for capability in self._capabilities.values()
            if query_lower in capability.metadata.id.lower()
            or query_lower in capability.metadata.name.lower()
            or query_lower in capability.metadata.display_name.lower()
            or any(query_lower in tag.lower() for tag in capability.metadata.tags)
        )

    def describe(self, capability_id: str) -> Capability:
        """Devuelve la capacidad ``capability_id``.

        Raises:
            CapabilityNotFoundException: si no existe.
        """
        capability = self.find(capability_id)
        if capability is None:
            raise CapabilityNotFoundException(f"La capacidad '{capability_id}' no existe.")
        return capability
