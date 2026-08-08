"""``JWTIdentityProvider`` — adapta un ``TokenProvider`` (JWT) al contrato ``IdentityProvider``.

Separado deliberadamente de ``JWTTokenProvider``
(``teaf/_internal/security/tokens/jwt_provider.py``): ese emite/verifica/
refresca/revoca tokens; este solo responde "¿quién es el llamante, según
el token que trae?" — la misma separación que existe entre
``ApiKeyProvider`` y ``ApiKeyIdentityProvider``.
"""

from __future__ import annotations

from teaf._internal.contracts.security import IdentityProvider, TokenProvider
from teaf._internal.security.exceptions import TokenException
from teaf._internal.security.models import AuthenticationCredentials, AuthenticationResult


class JWTIdentityProvider(IdentityProvider):
    """Autentica peticiones ``Authorization: Bearer <jwt>`` delegando en un ``TokenProvider``."""

    def __init__(self, *, token_provider: TokenProvider) -> None:
        self._token_provider = token_provider

    @property
    def provider_id(self) -> str:
        return "jwt"

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Verifica ``credentials.token`` contra el ``TokenProvider`` configurado."""
        if not credentials.token:
            raise TokenException("Falta el token JWT (scheme 'jwt' sin campo 'token').")
        identity = await self._token_provider.verify(credentials.token)
        return AuthenticationResult(identity=identity)

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        return credentials.scheme == self.provider_id and credentials.token is not None
