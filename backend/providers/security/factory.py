"""``SecurityFactory`` — construcción desacoplada de los managers de seguridad."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.providers.security.authentication_manager import AuthenticationManager
from backend.providers.security.authorization_manager import AuthorizationManager


class SecurityFactory(ABC):
    """Construye las piezas de seguridad de alto nivel consumidas por el framework."""

    @abstractmethod
    def create_authentication_manager(self) -> AuthenticationManager:
        """Devuelve un ``AuthenticationManager`` configurado y listo para usar."""
        ...

    @abstractmethod
    def create_authorization_manager(self) -> AuthorizationManager:
        """Devuelve un ``AuthorizationManager`` configurado y listo para usar."""
        ...
