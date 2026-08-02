"""``SecurityContext`` — identidad de seguridad de la petición en curso.

Mismo patrón que ``backend/core/context.py`` (correlation-id): un
``ContextVar`` con un valor por defecto seguro — aquí, un contexto
anónimo/no autenticado — consumible ya por cualquier router sin que exista
todavía un ``AuthenticationProvider`` real.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field

from backend.providers.security.rbac import Permission, Role


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Identidad de seguridad resuelta para la petición en curso."""

    principal_id: str | None = None
    roles: frozenset[Role] = field(default_factory=frozenset)

    @property
    def is_authenticated(self) -> bool:
        """``True`` si hay un principal identificado."""
        return self.principal_id is not None

    def has_permission(self, permission: Permission) -> bool:
        """``True`` si alguno de los roles del contexto otorga ``permission``."""
        return any(role.grants(permission) for role in self.roles)


#: Contexto por defecto fuera de una petición autenticada.
ANONYMOUS = SecurityContext()

_security_context_var: ContextVar[SecurityContext] = ContextVar(
    "security_context", default=ANONYMOUS
)


def set_security_context(context: SecurityContext) -> None:
    """Establece el contexto de seguridad de la petición en curso."""
    _security_context_var.set(context)


def get_security_context() -> SecurityContext:
    """Devuelve el contexto de seguridad de la petición en curso (``ANONYMOUS`` por defecto)."""
    return _security_context_var.get()
