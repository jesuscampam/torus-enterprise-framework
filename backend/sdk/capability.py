"""``ModuleCapability`` — declaración ligera de una capacidad que aporta un módulo.

Más simple que ``CapabilityBuilder``/``CapabilityMetadata``
(``backend.runtime.capabilities``): un módulo declara *qué* capacidad
aporta; ``CapabilityBinder`` (``capability_binder.py``) la traduce en una
``Capability`` real en el momento de registrar el módulo, completando
``provider``/``module`` automáticamente a partir del propio módulo — el
autor del módulo nunca construye una ``Capability`` a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.runtime.capabilities.enums import CapabilityCategory


@dataclass(frozen=True, slots=True)
class ModuleCapability:
    """Una capacidad que un módulo declara aportar al framework."""

    id: str
    name: str
    category: CapabilityCategory = CapabilityCategory.CUSTOM
    description: str = ""
    tags: tuple[str, ...] = ()
    experimental: bool = False

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta declaración."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "tags": list(self.tags),
            "experimental": self.experimental,
        }
