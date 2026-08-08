"""Role Based Endpoint — proteger un endpoint con ``@authorize(role=...)``.

Demuestra RBAC: un catálogo de roles (``StaticRoleResolver``) resuelve los
nombres de rol que trae un JWT (``identity.claims.roles``) a objetos
``Role``, y ``@authorize(role="admin")`` exige que el ``Principal`` de la
petición tenga alguno de los roles indicados.

Ejecutar:

    python examples/role-based-endpoint/main.py
"""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
)

jwt_provider = JWTProvider(secret="example-only-secret-do-not-use-in-production")
provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
)
role_resolver = StaticRoleResolver(
    roles_by_name={
        "admin": Role(name="admin"),
        "support": Role(name="support"),
    }
)
principal_resolver = PrincipalResolver(role_resolver=role_resolver)

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.post("/incidents/{incident_id}/close")
@authorize(role="admin")
def close_incident(incident_id: str) -> dict[str, object]:
    return {"incidentId": incident_id, "status": "closed"}


def _token_for(*, roles: frozenset[str]) -> str:
    identity = Identity(id="user-1", provider_id="jwt", claims=Claims(sub="user-1", roles=roles))
    pair = asyncio.run(jwt_provider.issue(identity))
    return pair.access_token


if __name__ == "__main__":
    support_token = _token_for(roles=frozenset({"support"}))
    admin_token = _token_for(roles=frozenset({"admin"}))

    with TestClient(app.asgi) as client:
        print("-- Rol 'support' (no autorizado) --")
        denied = client.post(
            "/incidents/42/close", headers={"Authorization": f"Bearer {support_token}"}
        )
        print(f"POST /incidents/42/close -> {denied.status_code}")

        print("\n-- Rol 'admin' (autorizado) --")
        allowed = client.post(
            "/incidents/42/close", headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"POST /incidents/42/close -> {allowed.status_code}: {allowed.json()}")
