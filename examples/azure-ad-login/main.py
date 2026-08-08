"""Azure AD Login — validar tokens de Microsoft Entra ID (OIDC + JWKS).

Demuestra ``AzureADProvider``: descubrimiento OIDC, validación de un JWT
RS256 contra el JWKS del tenant, y mapeo de claims propios de Azure AD
(``oid``, ``tid``, ``preferred_username``).

Este ejemplo mockea el tenant de Azure AD (``httpx.MockTransport``) para
poder ejecutarse sin credenciales ni red real — en producción se construye
``AzureADProvider(tenant=..., client_id=..., client_secret=...)`` sin
``http_client`` y habla con ``login.microsoftonline.com`` de verdad. También
muestra ``get_authorization_url()``, el primer paso real del Authorization
Code Flow (redirigir al usuario a Microsoft para iniciar sesión).

Ejecutar:

    python examples/azure-ad-login/main.py
"""

from __future__ import annotations

import asyncio
import base64
import time

import httpx
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    AzureADProvider,
    IdentityProviderRegistry,
    Principal,
    PrincipalResolver,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
    current_principal,
)

_TENANT_ID = "11111111-1111-1111-1111-111111111111"
_CLIENT_ID = "example-client-id"
_KEY_ID = "example-key-1"
_ISSUER = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _mock_azure_ad_transport(public_key: rsa.RSAPublicKey) -> httpx.MockTransport:
    """Simula el descubrimiento OIDC + JWKS de ``login.microsoftonline.com``."""
    numbers = public_key.public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": _KEY_ID,
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_uint(numbers.n),
                "e": _b64url_uint(numbers.e),
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == f"{_ISSUER}/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": _ISSUER,
                    "authorization_endpoint": f"{_ISSUER}/oauth2/v2.0/authorize",
                    "token_endpoint": f"{_ISSUER}/oauth2/v2.0/token",
                    "jwks_uri": f"{_ISSUER}/discovery/v2.0/keys",
                },
            )
        if str(request.url) == f"{_ISSUER}/discovery/v2.0/keys":
            return httpx.Response(200, json=jwks)
        return httpx.Response(404, json={"error": "not-found"})

    return httpx.MockTransport(handler)


def _issue_fake_azure_ad_token(private_key: rsa.RSAPrivateKey) -> str:
    now = int(time.time())
    payload = {
        "iss": _ISSUER,
        "aud": _CLIENT_ID,
        "sub": "azure-object-id",
        "oid": "azure-object-id",
        "tid": _TENANT_ID,
        "preferred_username": "alice@corp.example.com",
        "name": "Alice",
        "iat": now,
        "exp": now + 300,
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256", headers={"kid": _KEY_ID})


private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
http_client = httpx.AsyncClient(transport=_mock_azure_ad_transport(private_key.public_key()))
azure_ad_provider = AzureADProvider(
    tenant=_TENANT_ID, client_id=_CLIENT_ID, http_client=http_client
)

provider_registry = IdentityProviderRegistry([AnonymousIdentityProvider(), azure_ad_provider])
principal_resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={}))

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.get("/me")
@authorize()
def me(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    return {"id": principal.id, "email": principal.identity.claims.email}


if __name__ == "__main__":
    authorization_url = asyncio.run(
        azure_ad_provider.get_authorization_url(
            state="xyz", redirect_uri="https://app.example.com/callback"
        )
    )
    print(f"Paso 1 (real): redirigir al usuario a\n  {authorization_url}\n")

    token = _issue_fake_azure_ad_token(private_key)
    with TestClient(app.asgi) as client:
        print("-- Sin token --")
        anonymous = client.get("/me")
        print(f"GET /me (sin token) -> {anonymous.status_code}")

        print("\n-- Con el token de Azure AD (mockeado) --")
        authenticated = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        print(f"GET /me (con token) -> {authenticated.status_code}: {authenticated.json()}")

    asyncio.run(http_client.aclose())
