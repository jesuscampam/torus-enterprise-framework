"""Contratos de autenticación y autorización.

Ver docs/standards/SECURITY-STANDARD.md. Sin implementación real en este
Sprint: ninguna clase concreta de JWT/OAuth/RBAC existe todavía — solo el
contrato que esas implementaciones (Sprint 2.3+) deberán cumplir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuthenticationProvider(ABC):
    """Verifica la identidad de un llamante a partir de credenciales."""

    @abstractmethod
    async def authenticate(self, credentials: Any) -> Any:
        """Verifica ``credentials`` y devuelve el principal autenticado.

        Debe lanzar ``backend.core.exceptions.AuthenticationException`` si
        las credenciales son inválidas o han expirado. El tipo de
        ``credentials``/retorno lo define la implementación concreta
        (JWT, API key, etc.) — el contrato no impone un mecanismo.
        """
        ...


class AuthorizationProvider(ABC):
    """Decide si un principal autenticado puede realizar una acción sobre un recurso."""

    @abstractmethod
    async def authorize(self, principal: Any, *, resource: str, action: str) -> bool:
        """``True`` si ``principal`` puede ejecutar ``action`` sobre ``resource``.

        Debe lanzar ``backend.core.exceptions.AuthorizationException`` en
        vez de devolver ``False`` cuando la llamada espera que la ausencia
        de permiso interrumpa el flujo (la elección la hace el llamante).
        """
        ...
