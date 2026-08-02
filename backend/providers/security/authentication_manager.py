"""``AuthenticationManager`` — orquesta un ``AuthenticationProvider``.

Traduce el resultado de la autenticación a un ``SecurityContext`` del
framework, desacoplando a quien lo consume (futuros middlewares/routers)
del mecanismo concreto (JWT, OAuth, API key...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.contracts.security import AuthenticationProvider
from backend.providers.security.security_context import SecurityContext


class AuthenticationManager(ABC):
    """Orquesta la autenticación y construye el ``SecurityContext`` resultante."""

    def __init__(self, provider: AuthenticationProvider) -> None:
        self._provider = provider

    @abstractmethod
    async def authenticate(self, credentials: Any) -> SecurityContext:
        """Autentica ``credentials`` (vía ``self._provider``) y devuelve el ``SecurityContext``."""
        ...
