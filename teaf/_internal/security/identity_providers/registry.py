"""``IdentityProviderRegistry`` — enruta credenciales entrantes hacia el proveedor correcto.

Lo consume ``SecurityMiddleware``: en vez de que el middleware conozca
cada mecanismo concreto (JWT, API Key, LDAP, Azure AD...), pregunta al
registro "¿quién puede manejar esto?" — añadir un proveedor nuevo nunca
exige tocar el middleware, solo registrarlo aquí (directamente o vía
``SecurityModule``, ver ``teaf/_internal/modules/security/``).
"""

from __future__ import annotations

from collections.abc import Iterable

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.security.models import AuthenticationCredentials


class IdentityProviderRegistry:
    """Colección indexada de ``IdentityProvider`` con resolución por ``scheme``."""

    def __init__(self, providers: Iterable[IdentityProvider] = ()) -> None:
        self._providers: dict[str, IdentityProvider] = {p.provider_id: p for p in providers}

    def register(self, provider: IdentityProvider) -> None:
        """Registra (o reemplaza) ``provider`` por su ``provider_id``."""
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        """Elimina el proveedor ``provider_id`` si está registrado (no falla si no lo está)."""
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> IdentityProvider | None:
        """El proveedor registrado con ``provider_id``, o ``None``."""
        return self._providers.get(provider_id)

    def resolve(self, credentials: AuthenticationCredentials) -> IdentityProvider | None:
        """El proveedor que debe manejar ``credentials``, o ``None`` si ninguno aplica.

        Primero intenta una coincidencia exacta por ``credentials.scheme``
        (el caso común); si no hay proveedor registrado con ese id exacto,
        recorre el resto preguntando ``supports()`` — permite proveedores
        con lógica de enrutamiento más rica (p. ej. Azure AD reclamando un
        ``scheme="jwt"`` cuyo ``iss`` apunta a Microsoft).
        """
        exact = self._providers.get(credentials.scheme)
        if exact is not None and exact.supports(credentials):
            return exact
        for provider in self._providers.values():
            if provider is exact:
                continue
            if provider.supports(credentials):
                return provider
        return None

    @property
    def providers(self) -> tuple[IdentityProvider, ...]:
        """Todos los proveedores registrados, en orden de registro."""
        return tuple(self._providers.values())
