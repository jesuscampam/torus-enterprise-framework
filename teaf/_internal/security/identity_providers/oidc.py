"""``OpenIDConnectIdentityProvider`` — base OIDC genérica y reutilizable.

Implementa descubrimiento OIDC (``.well-known/openid-configuration``),
validación de tokens vía JWKS (``PyJWKClient``) y el Authorization Code
Flow — todo lo que un proveedor OIDC concreto necesita, sin acoplarse a
ninguno en particular. ``AzureADIdentityProvider`` es la primera
especialización concreta; Keycloak/Auth0/Okta/Google (ver ADR-007) solo
necesitan una subclase que fije ``discovery_url`` y, si sus claims no son
estándar, sobrescriba ``_map_claims`` — sin tocar la lógica de validación.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx
import jwt as pyjwt

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.security.exceptions import OidcException
from teaf._internal.security.models import (
    AuthenticationCredentials,
    AuthenticationResult,
    Claims,
    Identity,
)


@dataclass(frozen=True, slots=True)
class OidcDiscoveryDocument:
    """Los campos del documento de descubrimiento OIDC que este proveedor necesita."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None = None


class OpenIDConnectIdentityProvider(IdentityProvider):
    """Proveedor OIDC genérico: descubrimiento + validación JWKS + Authorization Code Flow."""

    def __init__(
        self,
        *,
        provider_id: str,
        discovery_url: str,
        client_id: str,
        client_secret: str | None = None,
        audience: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """``audience`` por defecto es ``client_id`` (el caso común: el token se emitió
        para esta aplicación). ``http_client`` se puede inyectar para pruebas
        (``httpx.MockTransport``) o para compartir un cliente entre varios
        proveedores OIDC de la misma aplicación."""
        self._provider_id = provider_id
        self._discovery_url = discovery_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._audience = audience or client_id
        self._http_client = http_client or httpx.AsyncClient()
        self._discovery: OidcDiscoveryDocument | None = None
        self._jwks: pyjwt.PyJWKSet | None = None

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def aclose(self) -> None:
        """Libera el cliente HTTP subyacente — llamar desde el ``dispose()`` del módulo."""
        await self._http_client.aclose()

    async def _discover(self) -> OidcDiscoveryDocument:
        """Descubre (y cachea) el documento OIDC en la primera llamada."""
        if self._discovery is not None:
            return self._discovery
        try:
            response = await self._http_client.get(self._discovery_url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise OidcException(
                f"Descubrimiento OIDC fallido en '{self._discovery_url}': {exc}"
            ) from exc

        self._discovery = OidcDiscoveryDocument(
            issuer=data["issuer"],
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            jwks_uri=data["jwks_uri"],
            userinfo_endpoint=data.get("userinfo_endpoint"),
        )
        return self._discovery

    async def _get_jwks(self, *, force_refresh: bool = False) -> pyjwt.PyJWKSet:
        """Obtiene (y cachea) el JWKS vía ``self._http_client`` — deliberadamente NO usa
        ``jwt.PyJWKClient`` porque ese cliente hace sus propias peticiones HTTP con
        ``urllib`` internamente, ignorando cualquier ``httpx.AsyncClient`` inyectado
        (rompe tanto el modelo async del framework como la inyección para pruebas)."""
        if self._jwks is not None and not force_refresh:
            return self._jwks
        discovery = await self._discover()
        try:
            response = await self._http_client.get(discovery.jwks_uri)
            response.raise_for_status()
            jwks_data = response.json()
        except httpx.HTTPError as exc:
            raise OidcException(
                f"No se pudo obtener JWKS de '{discovery.jwks_uri}': {exc}"
            ) from exc
        self._jwks = pyjwt.PyJWKSet.from_dict(jwks_data)
        return self._jwks

    async def _signing_key_for(self, token: str) -> pyjwt.PyJWK:
        """Resuelve la clave de verificación cuyo ``kid`` coincide con el del token.

        Si no se encuentra (p. ej. el emisor rotó sus claves después de la
        última vez que se cacheó el JWKS), refresca una vez antes de fallar.
        """
        try:
            kid = pyjwt.get_unverified_header(token).get("kid")
        except pyjwt.PyJWTError as exc:
            raise OidcException(f"No se pudo leer el header del token: {exc}") from exc

        jwks = await self._get_jwks()
        for key in jwks.keys:
            if key.key_id == kid:
                return key

        jwks = await self._get_jwks(force_refresh=True)
        for key in jwks.keys:
            if key.key_id == kid:
                return key

        raise OidcException(f"No se encontró una clave de firma con kid='{kid}' en el JWKS.")

    def _issuer_for_validation(self, discovery: OidcDiscoveryDocument) -> str | None:
        """El ``iss`` esperado, o ``None`` para omitir su validación estricta.

        Un proveedor multi-tenant (ver ``AzureADIdentityProvider``) puede
        sobrescribir esto porque el ``issuer`` del documento de
        descubrimiento "común" es un template, no un valor exacto — la
        validación real de tenant se hace sobre otro claim.
        """
        return discovery.issuer

    def _map_claims(self, payload: dict[str, Any]) -> Claims:
        """Mapeo OIDC estándar (``sub``/``name``/``email``) — sobrescribible por proveedor."""
        return Claims(
            sub=payload["sub"],
            name=payload.get("name"),
            email=payload.get("email"),
            extra=payload,
        )

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Valida ``credentials.token`` (un JWT firmado por este proveedor OIDC) contra su JWKS."""
        if not credentials.token:
            raise OidcException(f"Falta el token (scheme '{self.provider_id}').")

        discovery = await self._discover()
        signing_key = await self._signing_key_for(credentials.token)

        try:
            decode_kwargs: dict[str, Any] = {"audience": self._audience}
            expected_issuer = self._issuer_for_validation(discovery)
            if expected_issuer is not None:
                decode_kwargs["issuer"] = expected_issuer
            payload = pyjwt.decode(
                credentials.token, signing_key.key, algorithms=["RS256"], **decode_kwargs
            )
        except pyjwt.PyJWTError as exc:
            raise OidcException(f"Token OIDC inválido: {exc}") from exc

        claims = self._map_claims(payload)
        identity = Identity(id=claims.sub, provider_id=self.provider_id, claims=claims)
        return AuthenticationResult(identity=identity)

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        return credentials.scheme == self.provider_id and credentials.token is not None

    async def get_authorization_url(
        self, *, state: str, redirect_uri: str, scope: str = "openid profile email"
    ) -> str:
        """URL a la que redirigir al usuario para iniciar el Authorization Code Flow."""
        discovery = await self._discover()
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
        return f"{discovery.authorization_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str
    ) -> AuthenticationResult:
        """Intercambia ``code`` (recibido en el callback) por una identidad autenticada."""
        discovery = await self._discover()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._client_id,
        }
        if self._client_secret:
            data["client_secret"] = self._client_secret

        try:
            response = await self._http_client.post(discovery.token_endpoint, data=data)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OidcException(f"Intercambio de código OAuth2 fallido: {exc}") from exc

        token_response = response.json()
        id_token = token_response.get("id_token") or token_response.get("access_token")
        if not id_token:
            raise OidcException("La respuesta del token endpoint no incluyó id_token/access_token.")
        return await self.authenticate(
            AuthenticationCredentials(scheme=self.provider_id, token=id_token)
        )
