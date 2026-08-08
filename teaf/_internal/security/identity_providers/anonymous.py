"""``AnonymousIdentityProvider`` — el proveedor de respaldo, siempre disponible.

Nunca falla: cualquier credencial (o su ausencia) autentica como
identidad anónima. Es lo que usa ``SecurityMiddleware`` cuando ningún
otro proveedor reclama las credenciales de la petición y el endpoint
está marcado ``@allow_anonymous()`` — sin este proveedor, "sin
credenciales" tendría que ser un caso especial en el middleware en vez de
un proveedor de identidad más.
"""

from __future__ import annotations

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.security.models import (
    ANONYMOUS_IDENTITY,
    AuthenticationCredentials,
    AuthenticationResult,
)


class AnonymousIdentityProvider(IdentityProvider):
    """Siempre autentica con éxito, devolviendo la identidad anónima compartida."""

    @property
    def provider_id(self) -> str:
        return "anonymous"

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Ignora ``credentials`` — nunca lanza."""
        return AuthenticationResult(identity=ANONYMOUS_IDENTITY)

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        """Siempre ``True`` — es el proveedor de respaldo."""
        return True
