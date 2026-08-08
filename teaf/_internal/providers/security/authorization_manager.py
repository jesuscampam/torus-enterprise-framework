"""``AuthorizationManager`` — orquesta un ``AuthorizationProvider``.

Punto único de decisión de autorización consumido por futuros
middlewares/routers, desacoplado del mecanismo concreto (RBAC, ABAC...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from teaf._internal.contracts.security import AuthorizationProvider
from teaf._internal.providers.security.security_context import SecurityContext


class AuthorizationManager(ABC):
    """Orquesta la decisión de autorización para un ``SecurityContext`` dado."""

    def __init__(self, provider: AuthorizationProvider) -> None:
        self._provider = provider

    @abstractmethod
    async def authorize(self, context: SecurityContext, *, resource: str, action: str) -> bool:
        """``True`` si ``context`` puede ejecutar ``action`` sobre ``resource``."""
        ...
