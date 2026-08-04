"""Policy Based Endpoint — proteger un endpoint con ``@authorize(policy=...)``.

Una ``Policy`` decide con una función arbitraria sobre el ``Principal``, no
con un catálogo fijo de roles/permisos — aquí, "solo puede acceder al
panel del tenant 'acme' quien pertenece a ese mismo tenant" (multi-tenant),
una regla que un rol/permiso plano no puede expresar por sí solo (depende
de un dato del propio ``Principal`` — su tenant —, no de un conjunto fijo
de permisos).

Ejecutar:

    python examples/policy-based-endpoint/main.py
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
    Policy,
    PrincipalResolver,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
)

jwt_provider = JWTProvider(secret="example-only-secret-do-not-use-in-production")
provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
)
principal_resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={}))

belongs_to_acme = Policy(
    name="belongs-to-acme",
    rule=lambda principal: principal.tenant_id == "acme",
    description="Solo miembros del tenant 'acme' pueden acceder a su panel.",
)

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.get("/tenants/acme/settings")
@authorize(policy=belongs_to_acme)
def acme_tenant_settings() -> dict[str, object]:
    return {"tenantId": "acme", "settings": {"theme": "dark"}}


def _token_for(*, tenant: str) -> str:
    identity = Identity(id="user-1", provider_id="jwt", claims=Claims(sub="user-1", tenant=tenant))
    pair = asyncio.run(jwt_provider.issue(identity))
    return pair.access_token


if __name__ == "__main__":
    acme_token = _token_for(tenant="acme")
    other_token = _token_for(tenant="globex")

    with TestClient(app.asgi) as client:
        print("-- Miembro del tenant 'acme' --")
        allowed = client.get(
            "/tenants/acme/settings", headers={"Authorization": f"Bearer {acme_token}"}
        )
        print(f"GET /tenants/acme/settings -> {allowed.status_code}: {allowed.json()}")

        print("\n-- Miembro de otro tenant ('globex') --")
        denied = client.get(
            "/tenants/acme/settings", headers={"Authorization": f"Bearer {other_token}"}
        )
        print(f"GET /tenants/acme/settings -> {denied.status_code}")
