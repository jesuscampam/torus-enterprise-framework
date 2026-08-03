"""``ModuleHealth`` — declaración de una verificación de salud de un módulo.

Reutiliza ``CapabilityHealth`` (``backend.runtime.capabilities.enums``) en
vez de definir un vocabulario propio — un módulo y una capacidad comparten
el mismo concepto de salud (``UNKNOWN``/``HEALTHY``/``DEGRADED``/``UNHEALTHY``).
El SDK puede importar de ``backend/runtime/`` (la dependencia va en ese
sentido, nunca al revés — ver ``backend/sdk/__init__.py``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.runtime.capabilities.enums import CapabilityHealth


@dataclass(frozen=True, slots=True)
class ModuleHealth:
    """Una verificación de salud declarada por un módulo.

    ``check`` es opcional y sin uso automático en este Sprint — ningún
    scheduler ni endpoint invoca estas funciones todavía; es la forma que
    tendrá un Sprint futuro de conectar verificaciones en vivo.
    """

    name: str
    description: str = ""
    check: Callable[[], CapabilityHealth] | None = None

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta declaración."""
        return {
            "name": self.name,
            "description": self.description,
            "hasCheck": self.check is not None,
        }
