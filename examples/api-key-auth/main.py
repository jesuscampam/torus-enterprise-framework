"""API Key — emitir, usar, rotar y revocar una API Key.

Demuestra ``ApiKeyProvider`` (emisión/verificación/revocación/rotación,
independiente de HTTP) junto con ``ApiKeyIdentityProvider`` (el adaptador
que ``SecurityMiddleware`` usa para autenticar peticiones que traen la key
por header o query string) y cómo sus *scopes* se convierten en permisos
verificables con ``@authorize(permission=...)``.

Ejecutar:

    python examples/api-key-auth/main.py
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    ApiKeyIdentityProvider,
    ApiKeyProvider,
    IdentityProviderRegistry,
    Principal,
    PrincipalResolver,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
    current_principal,
)

api_key_provider = ApiKeyProvider(secret="example-only-secret-do-not-use-in-production")

provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), ApiKeyIdentityProvider(api_key_provider=api_key_provider)]
)
# Sin roles propios en este ejemplo — las API Keys autorizan por *scope*
# (convertido directamente en permiso, ver ApiKeyIdentityProvider), no por rol.
principal_resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={}))

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.get("/reports")
@authorize(permission="reports:read")
def reports(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    return {"principalId": principal.id, "reports": ["q1.csv", "q2.csv"]}


if __name__ == "__main__":
    # La emisión de una API Key es normalmente una operación administrativa
    # (un endpoint protegido, una consola interna) — aquí se hace directamente
    # sobre el provider para mantener el ejemplo enfocado en el flujo de uso.
    raw_key, record = api_key_provider.issue(
        principal_id="ci-pipeline", scopes=frozenset({"reports:read"})
    )
    print(f"API Key emitida para '{record.principal_id}' (id={record.id}): {raw_key}")

    with TestClient(app.asgi) as client:
        print("\n-- Sin API Key --")
        anonymous = client.get("/reports")
        print(f"GET /reports (sin key) -> {anonymous.status_code}")

        print("\n-- Con la API Key, vía header X-API-Key --")
        via_header = client.get("/reports", headers={"X-API-Key": raw_key})
        print(f"GET /reports (header) -> {via_header.status_code}: {via_header.json()}")

        print("\n-- Con la API Key, vía query string --")
        via_query = client.get("/reports", params={"api_key": raw_key})
        print(f"GET /reports (query) -> {via_query.status_code}: {via_query.json()}")

        print("\n-- Tras revocarla --")
        api_key_provider.revoke(record.id)
        revoked = client.get("/reports", headers={"X-API-Key": raw_key})
        print(f"GET /reports (revocada) -> {revoked.status_code}")

        print("\n-- Rotación: emitir una nueva clave para el mismo principal/scopes --")
        new_raw_key, new_record = api_key_provider.issue(
            principal_id="ci-pipeline", scopes=frozenset({"reports:read"})
        )
        rotated = client.get("/reports", headers={"X-API-Key": new_raw_key})
        print(f"GET /reports (nueva key) -> {rotated.status_code}: {rotated.json()}")
