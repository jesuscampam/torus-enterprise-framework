"""``ApiKeyIdentityProvider`` — adapta ``ApiKeyProvider`` al contrato ``IdentityProvider``.

Los *scopes* de la API Key se exponen como ``Claims.permissions`` — una
API Key no tiene nombre/email/roles como una identidad humana, así que
``Identity.claims`` solo rellena ``sub`` (el ``principal_id`` asociado a
la key) y ``permissions``; el resto queda vacío por diseño.
"""

from __future__ import annotations

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.security.exceptions import ApiKeyException
from teaf._internal.security.models import (
    AuthenticationCredentials,
    AuthenticationResult,
    Claims,
    Identity,
)
from teaf._internal.security.tokens.api_key_provider import ApiKeyProvider


class ApiKeyIdentityProvider(IdentityProvider):
    """Autentica peticiones que traen una API Key (header, query string o header propio)."""

    def __init__(self, *, api_key_provider: ApiKeyProvider) -> None:
        self._api_key_provider = api_key_provider

    @property
    def provider_id(self) -> str:
        return "api-key"

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Verifica ``credentials.api_key`` contra el ``ApiKeyProvider`` configurado."""
        if not credentials.api_key:
            raise ApiKeyException("Falta la API Key (scheme 'api-key' sin campo 'api_key').")
        record = self._api_key_provider.verify(credentials.api_key)
        claims = Claims(sub=record.principal_id, permissions=record.scopes)
        identity = Identity(id=record.principal_id, provider_id=self.provider_id, claims=claims)
        return AuthenticationResult(identity=identity)

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        return credentials.scheme == self.provider_id and credentials.api_key is not None
