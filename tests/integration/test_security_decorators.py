"""Pruebas de extremo a extremo de ``@authorize()``/``@allow_anonymous()`` y las
dependencias de FastAPI (``current_identity``/``current_principal``/``current_claims``/
``current_security_context``) contra un ``Application`` real."""

from __future__ import annotations

import asyncio

from fastapi import Depends
from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    Policy,
    Principal,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
    allow_anonymous,
    authorize,
    current_claims,
    current_identity,
    current_principal,
    current_security_context,
)


def _build_app():
    jwt_provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    registry = IdentityProviderRegistry(
        [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
    )
    role_resolver = StaticRoleResolver(
        roles_by_name={"admin": Role(name="admin", permissions=frozenset({"users:delete"}))}
    )
    principal_resolver = PrincipalResolver(role_resolver=role_resolver)

    app = Application()
    app.asgi.add_middleware(
        SecurityMiddleware, provider_registry=registry, principal_resolver=principal_resolver
    )

    same_tenant_policy = Policy(name="acme-tenant", rule=lambda p: p.tenant_id == "acme")

    @app.asgi.get("/public")
    @allow_anonymous()
    def public_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/must-be-authenticated")
    @authorize()
    def must_be_authenticated() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/admin-role")
    @authorize(role="admin")
    def admin_role_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/delete-permission")
    @authorize(permission="users:delete")
    def delete_permission_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/acme-tenant")
    @authorize(policy=same_tenant_policy)
    def acme_tenant_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/multi-role")
    @authorize(role=["admin", "editor"])
    def multi_role_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/async-admin-role")
    @authorize(role="admin")
    async def async_admin_role_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @app.asgi.get("/deps/identity")
    def identity_endpoint(identity: Identity = Depends(current_identity)) -> dict[str, object]:
        return {"id": identity.id, "authenticated": identity.authenticated}

    @app.asgi.get("/deps/principal")
    def principal_endpoint(principal: Principal = Depends(current_principal)) -> dict[str, object]:
        return {"id": principal.id, "isAuthenticated": principal.is_authenticated}

    @app.asgi.get("/deps/claims")
    def claims_endpoint(claims: Claims = Depends(current_claims)) -> dict[str, object]:
        return {"sub": claims.sub}

    @app.asgi.get("/deps/context")
    def context_endpoint(ctx=Depends(current_security_context)) -> dict[str, object]:
        return {"principalId": ctx.principal_id}

    return app, jwt_provider


def _issue_token(
    jwt_provider: JWTProvider, *, roles: frozenset[str] = frozenset(), tenant: str | None = None
) -> str:
    identity = Identity(
        id="alice", provider_id="jwt", claims=Claims(sub="alice", roles=roles, tenant=tenant)
    )
    pair = asyncio.run(jwt_provider.issue(identity))
    return pair.access_token


def test_allow_anonymous_endpoint_is_always_reachable() -> None:
    app, _ = _build_app()
    with TestClient(app.asgi) as client:
        assert client.get("/public").status_code == 200


def test_authorize_without_arguments_requires_authentication() -> None:
    app, jwt_provider = _build_app()
    with TestClient(app.asgi) as client:
        assert client.get("/must-be-authenticated").status_code == 401

        token = _issue_token(jwt_provider)
        response = client.get(
            "/must-be-authenticated", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


def test_authorize_role_rejects_authenticated_user_without_the_role() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider)  # sin roles
    with TestClient(app.asgi) as client:
        response = client.get("/admin-role", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


def test_authorize_role_allows_authenticated_user_with_the_role() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider, roles=frozenset({"admin"}))
    with TestClient(app.asgi) as client:
        response = client.get("/admin-role", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200


def test_authorize_permission_allows_only_when_role_grants_it() -> None:
    app, jwt_provider = _build_app()
    token_without_role = _issue_token(jwt_provider)
    token_with_role = _issue_token(jwt_provider, roles=frozenset({"admin"}))

    with TestClient(app.asgi) as client:
        denied = client.get(
            "/delete-permission", headers={"Authorization": f"Bearer {token_without_role}"}
        )
        assert denied.status_code == 403

        allowed = client.get(
            "/delete-permission", headers={"Authorization": f"Bearer {token_with_role}"}
        )
        assert allowed.status_code == 200


def test_authorize_policy_evaluates_against_the_resolved_principal() -> None:
    app, jwt_provider = _build_app()
    matching_token = _issue_token(jwt_provider, tenant="acme")
    other_token = _issue_token(jwt_provider, tenant="other")

    with TestClient(app.asgi) as client:
        matching = client.get("/acme-tenant", headers={"Authorization": f"Bearer {matching_token}"})
        assert matching.status_code == 200

        other = client.get("/acme-tenant", headers={"Authorization": f"Bearer {other_token}"})
        assert other.status_code == 403


def test_authorize_role_accepts_a_list_and_matches_any_one_of_them() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider, roles=frozenset({"admin"}))
    with TestClient(app.asgi) as client:
        response = client.get("/multi-role", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200


def test_authorize_works_on_an_async_endpoint() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider, roles=frozenset({"admin"}))
    with TestClient(app.asgi) as client:
        allowed = client.get("/async-admin-role", headers={"Authorization": f"Bearer {token}"})
        assert allowed.status_code == 200

        other_token = _issue_token(jwt_provider)
        denied = client.get("/async-admin-role", headers={"Authorization": f"Bearer {other_token}"})
        assert denied.status_code == 403


def test_current_identity_dependency_returns_anonymous_identity_by_default() -> None:
    app, _ = _build_app()
    with TestClient(app.asgi) as client:
        response = client.get("/deps/identity")
        assert response.json() == {"id": "anonymous", "authenticated": False}


def test_current_identity_dependency_returns_the_authenticated_identity() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider)
    with TestClient(app.asgi) as client:
        response = client.get("/deps/identity", headers={"Authorization": f"Bearer {token}"})
        assert response.json() == {"id": "alice", "authenticated": True}


def test_current_principal_dependency() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider, roles=frozenset({"admin"}))
    with TestClient(app.asgi) as client:
        response = client.get("/deps/principal", headers={"Authorization": f"Bearer {token}"})
        assert response.json() == {"id": "alice", "isAuthenticated": True}


def test_current_claims_dependency() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider)
    with TestClient(app.asgi) as client:
        response = client.get("/deps/claims", headers={"Authorization": f"Bearer {token}"})
        assert response.json() == {"sub": "alice"}


def test_current_security_context_dependency() -> None:
    app, jwt_provider = _build_app()
    token = _issue_token(jwt_provider)
    with TestClient(app.asgi) as client:
        response = client.get("/deps/context", headers={"Authorization": f"Bearer {token}"})
        assert response.json() == {"principalId": "alice"}
