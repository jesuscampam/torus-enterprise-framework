"""Pruebas de extremo a extremo de ``SecurityMiddleware`` contra un ``Application`` real.

Cubre el "sniffing" de credenciales (Bearer JWT/Azure AD, Basic → LDAP, API Key vía
header o query string, anónimo por defecto) y los eventos de autenticación publicados.
"""

from __future__ import annotations

import asyncio
import base64

from fastapi import Request
from fastapi.testclient import TestClient
from teaf import Application
from teaf._internal.providers.security.security_context import get_security_context
from teaf._internal.runtime.event_bus import EventBus
from teaf.security import (
    AnonymousIdentityProvider,
    ApiKeyIdentityProvider,
    ApiKeyProvider,
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
)


def _build_app(*, event_bus: EventBus | None = None):
    jwt_provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    api_key_provider = ApiKeyProvider(secret="test-secret-with-at-least-32-bytes!!")
    registry = IdentityProviderRegistry(
        [
            AnonymousIdentityProvider(),
            JWTIdentityProvider(token_provider=jwt_provider),
            ApiKeyIdentityProvider(api_key_provider=api_key_provider),
        ]
    )
    role_resolver = StaticRoleResolver(
        roles_by_name={"admin": Role(name="admin", permissions=frozenset({"users:delete"}))}
    )
    principal_resolver = PrincipalResolver(role_resolver=role_resolver)

    app = Application()
    app.asgi.add_middleware(
        SecurityMiddleware,
        provider_registry=registry,
        principal_resolver=principal_resolver,
        event_bus=event_bus,
    )

    @app.asgi.get("/context")
    def context_endpoint(request: Request) -> dict[str, object]:
        ctx = get_security_context()
        return {
            "principalId": ctx.principal_id,
            "isAuthenticated": ctx.is_authenticated,
            "roles": sorted(role.name for role in ctx.roles),
            "permissions": sorted(ctx.permissions),
            "providerId": ctx.provider_id,
        }

    return app, jwt_provider, api_key_provider


def test_request_without_credentials_resolves_to_anonymous() -> None:
    app, _, _ = _build_app()
    with TestClient(app.asgi) as client:
        response = client.get("/context")
        assert response.status_code == 200
        body = response.json()
        assert body["isAuthenticated"] is False
        assert body["providerId"] == "anonymous"


def test_bearer_jwt_token_resolves_identity_and_roles() -> None:
    app, jwt_provider, _ = _build_app()
    identity = Identity(
        id="alice", provider_id="jwt", claims=Claims(sub="alice", roles=frozenset({"admin"}))
    )
    pair = asyncio.run(jwt_provider.issue(identity))

    with TestClient(app.asgi) as client:
        response = client.get("/context", headers={"Authorization": f"Bearer {pair.access_token}"})
        body = response.json()
        assert body["isAuthenticated"] is True
        assert body["principalId"] == "alice"
        assert body["roles"] == ["admin"]
        assert body["permissions"] == ["users:delete"]
        assert body["providerId"] == "jwt"


def test_bearer_with_invalid_jwt_falls_back_to_anonymous() -> None:
    app, _, _ = _build_app()
    with TestClient(app.asgi) as client:
        response = client.get("/context", headers={"Authorization": "Bearer not-a-real-token"})
        assert response.status_code == 200
        assert response.json()["isAuthenticated"] is False


def test_api_key_header_resolves_identity_and_scopes_as_permissions() -> None:
    app, _, api_key_provider = _build_app()
    raw_key, _ = api_key_provider.issue(principal_id="bob", scopes=frozenset({"users:read"}))

    with TestClient(app.asgi) as client:
        response = client.get("/context", headers={"X-API-Key": raw_key})
        body = response.json()
        assert body["isAuthenticated"] is True
        assert body["principalId"] == "bob"
        assert body["permissions"] == ["users:read"]
        assert body["providerId"] == "api-key"


def test_api_key_query_param_also_resolves_identity() -> None:
    app, _, api_key_provider = _build_app()
    raw_key, _ = api_key_provider.issue(principal_id="bob")

    with TestClient(app.asgi) as client:
        response = client.get("/context", params={"api_key": raw_key})
        assert response.json()["isAuthenticated"] is True


def test_basic_auth_header_is_routed_to_the_ldap_scheme() -> None:
    """Sin ``LDAPProvider`` registrado, el registro no resuelve ningún proveedor y
    la petición cae a anónimo — confirma el *routing*, no requiere un servidor LDAP real."""
    app, _, _ = _build_app()
    credentials = base64.b64encode(b"alice:secret").decode("ascii")

    with TestClient(app.asgi) as client:
        response = client.get("/context", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code == 200
        assert response.json()["isAuthenticated"] is False


def test_authentication_events_are_published() -> None:
    event_bus = EventBus()
    published: list[str] = []
    event_bus.subscribe("authentication.started", lambda event: published.append(event.name))
    event_bus.subscribe("authentication.succeeded", lambda event: published.append(event.name))

    app, jwt_provider, _ = _build_app(event_bus=event_bus)
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice"))
    pair = asyncio.run(jwt_provider.issue(identity))

    with TestClient(app.asgi) as client:
        client.get("/context", headers={"Authorization": f"Bearer {pair.access_token}"})

    assert published == ["authentication.started", "authentication.succeeded"]


def test_authentication_failed_event_is_published_for_an_invalid_token() -> None:
    event_bus = EventBus()
    published: list[str] = []
    event_bus.subscribe("authentication.failed", lambda event: published.append(event.name))

    app, _, _ = _build_app(event_bus=event_bus)

    with TestClient(app.asgi) as client:
        client.get("/context", headers={"Authorization": "Bearer not-a-real-token"})

    assert published == ["authentication.failed"]
