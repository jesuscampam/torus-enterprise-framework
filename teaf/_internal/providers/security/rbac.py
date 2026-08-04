"""Abstracciones RBAC (Role-Based Access Control).

Estructuras de datos puras — sin persistencia ni lógica de asignación
real, ver docs/standards/SECURITY-STANDARD.md, sección 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Un permiso es un identificador de acción sobre un recurso, p. ej.
#: "incidents:read" — el formato concreto lo define cada aplicación futura.
Permission = str


@dataclass(frozen=True, slots=True)
class Role:
    """Rol con un nombre y el conjunto de permisos que otorga."""

    name: str
    permissions: frozenset[Permission] = field(default_factory=frozenset)

    def grants(self, permission: Permission) -> bool:
        """``True`` si este rol incluye ``permission``."""
        return permission in self.permissions
