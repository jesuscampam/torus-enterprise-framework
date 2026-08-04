"""``ModuleConfiguration`` — declaración de una clave de configuración que un módulo necesita.

Puramente declarativa: no lee variables de entorno ni valida contra
``backend/config/`` — un módulo real conectará esto a configuración real en
un Sprint futuro. Aquí solo se documenta *qué* configuración requiere el
módulo, consumido por ``ModuleValidator`` y ``ModuleDocumentationGenerator``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModuleConfiguration:
    """Una clave de configuración declarada por un módulo."""

    key: str
    description: str = ""
    required: bool = False
    default: object | None = None
    sensitive: bool = False

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta declaración.

        ``default`` se omite si ``sensitive`` es ``True`` — nunca se expone
        un valor por defecto potencialmente sensible en documentación o
        respuestas de introspección.
        """
        return {
            "key": self.key,
            "description": self.description,
            "required": self.required,
            "default": None if self.sensitive else self.default,
            "sensitive": self.sensitive,
        }
