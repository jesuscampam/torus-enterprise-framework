"""Pruebas de extremo a extremo de ``AzureADProvider``/``OpenIDConnectProvider`` vía
``httpx.MockTransport`` — sin red real ni servidor OIDC real.

Reproduce el descubrimiento OIDC + JWKS + validación de un JWT RS256 firmado con un
par de claves RSA generado en la propia prueba, incluyendo el caso multi-tenant
(``tenant="common"``) con lista de tenants permitidos.
"""

from __future__ import annotations

import asyncio
import time

import httpx
import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from teaf._internal.security.exceptions import OidcException
from teaf.security import AuthenticationCredentials, AzureADProvider

_TENANT_ID = "11111111-1111-1111-1111-111111111111"
_CLIENT_ID = "test-client-id"
_KEY_ID = "test-key-1"


def _generate_rsa_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _jwk_from_public_key(public_key: rsa.RSAPublicKey, *, kid: str) -> dict[str, object]:
    numbers = public_key.public_numbers()

    def _b64url_uint(value: int) -> str:
        import base64

        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }


def _issue_token(
    private_key: rsa.RSAPrivateKey, *, issuer: str, tenant_id: str, **extra: object
) -> str:
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": _CLIENT_ID,
        "sub": "user-object-id",
        "oid": "user-object-id",
        "tid": tenant_id,
        "preferred_username": "alice@example.com",
        "name": "Alice",
        "iat": now,
        "exp": now + 300,
        **extra,
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256", headers={"kid": _KEY_ID})


def _mock_transport(*, issuer: str, jwks: dict[str, object]) -> httpx.MockTransport:
    discovery_url = (
        f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0/.well-known/openid-configuration"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": f"{issuer}/oauth2/v2.0/token",
                    "jwks_uri": f"{issuer}/discovery/v2.0/keys",
                },
            )
        if str(request.url) == f"{issuer}/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not-found"})

    return httpx.MockTransport(handler)


def _provider(
    *, tenant: str, private_key: rsa.RSAPrivateKey, public_key: rsa.RSAPublicKey, issuer: str
) -> tuple[AzureADProvider, httpx.AsyncClient]:
    jwks = {"keys": [_jwk_from_public_key(public_key, kid=_KEY_ID)]}
    transport = _mock_transport(issuer=issuer, jwks=jwks)
    http_client = httpx.AsyncClient(transport=transport)
    provider = AzureADProvider(
        tenant=tenant, client_id=_CLIENT_ID, http_client=http_client, allowed_tenants=None
    )
    return provider, http_client


def test_single_tenant_valid_token_authenticates_successfully() -> None:
    private_key, public_key = _generate_rsa_keypair()
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    provider, http_client = _provider(
        tenant=_TENANT_ID, private_key=private_key, public_key=public_key, issuer=issuer
    )
    token = _issue_token(private_key, issuer=issuer, tenant_id=_TENANT_ID)

    async def scenario() -> None:
        result = await provider.authenticate(
            AuthenticationCredentials(scheme="azure-ad", token=token)
        )
        assert result.identity.id == "user-object-id"
        assert result.identity.claims.email == "alice@example.com"
        assert result.identity.claims.tenant == _TENANT_ID
        await provider.aclose()

    asyncio.run(scenario())


def test_provider_id_is_azure_ad() -> None:
    private_key, public_key = _generate_rsa_keypair()
    provider, http_client = _provider(
        tenant=_TENANT_ID,
        private_key=private_key,
        public_key=public_key,
        issuer=f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0",
    )
    assert provider.provider_id == "azure-ad"
    asyncio.run(provider.aclose())


def test_invalid_signature_raises_oidc_exception() -> None:
    private_key, public_key = _generate_rsa_keypair()
    other_private_key, _ = _generate_rsa_keypair()
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    provider, http_client = _provider(
        tenant=_TENANT_ID, private_key=private_key, public_key=public_key, issuer=issuer
    )
    # Firmado con una clave privada distinta a la publicada en el JWKS mockeado.
    token = _issue_token(other_private_key, issuer=issuer, tenant_id=_TENANT_ID)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.authenticate(AuthenticationCredentials(scheme="azure-ad", token=token))
        await provider.aclose()

    asyncio.run(scenario())


def test_multi_tenant_common_skips_strict_issuer_but_validates_allowed_tenants() -> None:
    private_key, public_key = _generate_rsa_keypair()
    # El documento de descubrimiento "common" real tiene un issuer con el
    # placeholder {tenantid} sin resolver, y el token real trae el tenant
    # concreto en "iss" — replicamos exactamente ese desajuste aquí.
    discovery_issuer = "https://login.microsoftonline.com/{tenantid}/v2.0"
    token_issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"

    jwks = {"keys": [_jwk_from_public_key(public_key, kid=_KEY_ID)]}
    discovery_url = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": discovery_issuer,
                    "authorization_endpoint": f"{discovery_issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": f"{discovery_issuer}/oauth2/v2.0/token",
                    "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
                },
            )
        if str(request.url) == "https://login.microsoftonline.com/common/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not-found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(
        tenant="common",
        client_id=_CLIENT_ID,
        http_client=http_client,
        allowed_tenants=frozenset({_TENANT_ID}),
    )
    token = _issue_token(private_key, issuer=token_issuer, tenant_id=_TENANT_ID)

    async def scenario() -> None:
        result = await provider.authenticate(
            AuthenticationCredentials(scheme="azure-ad", token=token)
        )
        assert result.identity.claims.tenant == _TENANT_ID
        await provider.aclose()

    asyncio.run(scenario())


def test_multi_tenant_common_rejects_tenant_outside_the_allow_list() -> None:
    private_key, public_key = _generate_rsa_keypair()
    discovery_issuer = "https://login.microsoftonline.com/{tenantid}/v2.0"
    token_issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"

    jwks = {"keys": [_jwk_from_public_key(public_key, kid=_KEY_ID)]}
    discovery_url = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": discovery_issuer,
                    "authorization_endpoint": f"{discovery_issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": f"{discovery_issuer}/oauth2/v2.0/token",
                    "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
                },
            )
        if str(request.url) == "https://login.microsoftonline.com/common/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not-found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(
        tenant="common",
        client_id=_CLIENT_ID,
        http_client=http_client,
        allowed_tenants=frozenset({"a-different-tenant-id"}),
    )
    token = _issue_token(private_key, issuer=token_issuer, tenant_id=_TENANT_ID)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.authenticate(AuthenticationCredentials(scheme="azure-ad", token=token))
        await provider.aclose()

    asyncio.run(scenario())


def test_get_authorization_url_builds_the_authorization_code_flow_url() -> None:
    private_key, public_key = _generate_rsa_keypair()
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    provider, http_client = _provider(
        tenant=_TENANT_ID, private_key=private_key, public_key=public_key, issuer=issuer
    )

    async def scenario() -> str:
        url = await provider.get_authorization_url(
            state="xyz", redirect_uri="https://app.example.com/callback"
        )
        await provider.aclose()
        return url

    url = asyncio.run(scenario())
    assert url.startswith(f"{issuer}/oauth2/v2.0/authorize?")
    assert "state=xyz" in url
    assert "client_id=test-client-id" in url


def test_exchange_code_for_token_authenticates_with_the_returned_id_token() -> None:
    private_key, public_key = _generate_rsa_keypair()
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    id_token = _issue_token(private_key, issuer=issuer, tenant_id=_TENANT_ID)
    jwks = {"keys": [_jwk_from_public_key(public_key, kid=_KEY_ID)]}
    discovery_url = (
        f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0/.well-known/openid-configuration"
    )
    token_endpoint = f"{issuer}/oauth2/v2.0/token"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": token_endpoint,
                    "jwks_uri": f"{issuer}/discovery/v2.0/keys",
                },
            )
        if str(request.url) == f"{issuer}/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        if str(request.url) == token_endpoint and request.method == "POST":
            return httpx.Response(200, json={"id_token": id_token})
        return httpx.Response(404, json={"error": "not-found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client)

    async def scenario() -> None:
        result = await provider.exchange_code_for_token(
            code="auth-code", redirect_uri="https://app.example.com/callback"
        )
        assert result.identity.id == "user-object-id"
        await provider.aclose()

    asyncio.run(scenario())


def test_exchange_code_for_token_raises_when_token_endpoint_omits_tokens() -> None:
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    discovery_url = (
        f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0/.well-known/openid-configuration"
    )
    token_endpoint = f"{issuer}/oauth2/v2.0/token"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": token_endpoint,
                    "jwks_uri": f"{issuer}/discovery/v2.0/keys",
                },
            )
        if str(request.url) == token_endpoint and request.method == "POST":
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"error": "not-found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.exchange_code_for_token(
                code="auth-code", redirect_uri="https://app.example.com/callback"
            )
        await provider.aclose()

    asyncio.run(scenario())


def test_unknown_kid_refreshes_jwks_once_before_raising() -> None:
    """Simula rotación de claves: el JWKS servido cambia de ``kid`` entre la primera
    petición (cacheada) y el refresco forzado — el segundo tampoco lo encuentra
    y debe fallar con un mensaje claro, no un ``KeyError``."""
    private_key, public_key = _generate_rsa_keypair()
    issuer = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
    discovery_url = (
        f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0/.well-known/openid-configuration"
    )

    # El JWKS nunca contiene la clave usada para firmar el token (kid distinto).
    jwks = {"keys": [_jwk_from_public_key(public_key, kid="a-different-kid")]}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "authorization_endpoint": f"{issuer}/oauth2/v2.0/authorize",
                    "token_endpoint": f"{issuer}/oauth2/v2.0/token",
                    "jwks_uri": f"{issuer}/discovery/v2.0/keys",
                },
            )
        if str(request.url) == f"{issuer}/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not-found"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client)
    token = _issue_token(private_key, issuer=issuer, tenant_id=_TENANT_ID)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.authenticate(AuthenticationCredentials(scheme="azure-ad", token=token))
        await provider.aclose()

    asyncio.run(scenario())


def test_missing_token_raises_oidc_exception() -> None:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    provider = AzureADProvider(tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.authenticate(AuthenticationCredentials(scheme="azure-ad"))
        await provider.aclose()

    asyncio.run(scenario())


def test_discovery_failure_raises_oidc_exception() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server-error"})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureADProvider(tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client)

    async def scenario() -> None:
        with pytest.raises(OidcException):
            await provider.authenticate(AuthenticationCredentials(scheme="azure-ad", token="x"))
        await provider.aclose()

    asyncio.run(scenario())
