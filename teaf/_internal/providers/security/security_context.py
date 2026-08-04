"""``SecurityContext`` — identidad de seguridad de la petición en curso.

Mismo patrón que ``backend/core/context.py`` (correlation-id): un
``ContextVar`` con un valor por defecto seguro — aquí, un contexto
anónimo/no autenticado — consumible ya por cualquier router sin que exista
todavía un ``AuthenticationProvider`` real.

Desde Sprint 2.7 (Enterprise Security Platform, ver ADR-007) se extiende
de forma aditiva: los campos nuevos (``identity``, ``principal``,
``permissions``, ``tenant_id``, ``provider_id``, ``correlation_id``,
``request_id``) tienen todos un valor por defecto, así que cualquier
código existente que construya ``SecurityContext(principal_id=..., roles=...)``
sigue funcionando exactamente igual. ``identity``/``principal`` se
referencian solo a nivel de tipo (``TYPE_CHECKING``) para no introducir
una dependencia en tiempo de ejecución de ``providers/security/`` (Sprint
2.2) hacia ``security/`` (Sprint 2.7) — la dirección de dependencias real
sigue yendo de ``security/`` hacia aquí (reutiliza ``Role``/``Permission``),
nunca al revés.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from teaf._internal.providers.security.rbac import Permission, Role

if TYPE_CHECKING:
    from teaf._internal.security.models import Identity, Principal


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Identidad de seguridad resuelta para la petición en curso."""

    principal_id: str | None = None
    roles: frozenset[Role] = field(default_factory=frozenset)
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    identity: Identity | None = None
    principal: Principal | None = None
    tenant_id: str | None = None
    provider_id: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """``True`` si hay un principal identificado."""
        return self.principal_id is not None

    def has_permission(self, permission: Permission) -> bool:
        """``True`` si ``permission`` está en ``permissions`` o la otorga algún rol."""
        if permission in self.permissions:
            return True
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
