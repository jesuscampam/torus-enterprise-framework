"""Permission Based Endpoint — proteger un endpoint con ``@authorize(permission=...)``.

A diferencia de un chequeo por rol, un chequeo por permiso no le importa
*qué rol* tiene el ``Principal`` — solo que alguno de sus roles (o sus
permisos directos) otorgue el permiso exigido. Aquí dos roles distintos
("admin" y "billing-operator") otorgan el mismo permiso ("invoices:void"),
y el endpoint acepta a cualquiera de los dos sin conocer sus nombres.

Ejecutar:

    python examples/permission-based-endpoint/main.py
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
        "admin": Role(name="admin", permissions=frozenset({"invoices:void"})),
        "billing-operator": Role(
            name="billing-operator", permissions=frozenset({"invoices:void", "invoices:read"})
        ),
        "support": Role(name="support", permissions=frozenset({"invoices:read"})),
    }
)
principal_resolver = PrincipalResolver(role_resolver=role_resolver)

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.post("/invoices/{invoice_id}/void")
@authorize(permission="invoices:void")
def void_invoice(invoice_id: str) -> dict[str, object]:
    return {"invoiceId": invoice_id, "status": "voided"}


def _token_for(*, roles: frozenset[str]) -> str:
    identity = Identity(id="user-1", provider_id="jwt", claims=Claims(sub="user-1", roles=roles))
    pair = asyncio.run(jwt_provider.issue(identity))
    return pair.access_token


if __name__ == "__main__":
    support_token = _token_for(roles=frozenset({"support"}))  # solo invoices:read
    billing_token = _token_for(roles=frozenset({"billing-operator"}))  # sí tiene invoices:void

    with TestClient(app.asgi) as client:
        print("-- Rol 'support' (sin el permiso 'invoices:void') --")
        denied = client.post(
            "/invoices/7/void", headers={"Authorization": f"Bearer {support_token}"}
        )
        print(f"POST /invoices/7/void -> {denied.status_code}")

        print("\n-- Rol 'billing-operator' (con el permiso 'invoices:void') --")
        allowed = client.post(
            "/invoices/7/void", headers={"Authorization": f"Bearer {billing_token}"}
        )
        print(f"POST /invoices/7/void -> {allowed.status_code}: {allowed.json()}")
