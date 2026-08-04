"""Anonymous Endpoint — marcar explícitamente un endpoint como público con ``@allow_anonymous()``.

``SecurityMiddleware`` nunca bloquea una petición por falta de
autenticación — un endpoint sin ``@authorize()`` ya es accesible sin
credenciales. ``@allow_anonymous()`` no cambia ese comportamiento (es un
no-op en tiempo de ejecución): existe para dejar la intención explícita en
el código ("sí, este endpoint es público a propósito"), documentación
ejecutable que contrasta claramente con un ``@authorize()`` al lado.

Ejecutar:

    python examples/anonymous-endpoint/main.py
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    IdentityProviderRegistry,
    Principal,
    PrincipalResolver,
    SecurityMiddleware,
    StaticRoleResolver,
    allow_anonymous,
    authorize,
    current_principal,
)

provider_registry = IdentityProviderRegistry([AnonymousIdentityProvider()])
principal_resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={}))

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.get("/status")
@allow_anonymous()
def status(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    """Público a propósito: cualquiera puede consultar el estado del servicio."""
    return {"status": "ok", "requestedBy": principal.id}


@app.asgi.get("/account")
@authorize()
def account(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    """Contraste: este sí exige autenticación."""
    return {"accountId": principal.id}


if __name__ == "__main__":
    with TestClient(app.asgi) as client:
        print("-- /status, sin credenciales --")
        status_response = client.get("/status")
        print(f"GET /status -> {status_response.status_code}: {status_response.json()}")

        print("\n-- /account, sin credenciales --")
        account_response = client.get("/account")
        print(f"GET /account -> {account_response.status_code}")
