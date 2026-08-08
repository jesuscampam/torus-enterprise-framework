"""JWT Login — autenticar con usuario/contraseña y emitir un access + refresh token.

Demuestra el flujo completo: ``PasswordHasher`` (Argon2id) para verificar la
contraseña contra un "almacén" de usuarios de juguete, ``JWTProvider`` para
emitir el ``TokenPair`` tras un login válido, y ``SecurityMiddleware`` +
``@authorize()`` para proteger un endpoint con el token emitido.

Ejecutar:

    python examples/jwt-login/main.py
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    Argon2PasswordHasher,
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    Principal,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
    current_principal,
)

# -- Infraestructura de seguridad (normalmente construida una vez, al arrancar la app) --

password_hasher = Argon2PasswordHasher()
jwt_provider = JWTProvider(secret="example-only-secret-do-not-use-in-production")

# Almacén de usuarios de juguete: username -> (hash de contraseña, roles).
# Una aplicación real lo reemplaza por un repositorio contra su base de datos.
_USERS = {
    "alice": (password_hasher.hash("correct-horse-battery-staple"), frozenset({"admin"})),
}

provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
)
role_resolver = StaticRoleResolver(
    roles_by_name={"admin": Role(name="admin", permissions=frozenset({"users:delete"}))}
)
principal_resolver = PrincipalResolver(role_resolver=role_resolver)

# -- Aplicación -------------------------------------------------------------------------

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.post("/login")
async def login(username: str, password: str) -> dict[str, object]:
    """Verifica ``username``/``password`` y, si son correctas, emite un ``TokenPair``."""
    record = _USERS.get(username)
    if record is None or not password_hasher.verify(password, record[0]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    _, roles = record
    identity = Identity(id=username, provider_id="jwt", claims=Claims(sub=username, roles=roles))
    token_pair = await jwt_provider.issue(identity)
    return token_pair.as_dict()


@app.asgi.get("/me")
@authorize()
def me(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    """Requiere un access token válido (``@authorize()`` sin argumentos)."""
    return {"id": principal.id, "roles": sorted(role.name for role in principal.roles)}


if __name__ == "__main__":
    with TestClient(app.asgi) as client:
        print("-- Login con credenciales incorrectas --")
        failed = client.post("/login", params={"username": "alice", "password": "wrong"})
        print(f"POST /login -> {failed.status_code}: {failed.json()}")

        print("\n-- Login con credenciales correctas --")
        ok = client.post(
            "/login", params={"username": "alice", "password": "correct-horse-battery-staple"}
        )
        print(f"POST /login -> {ok.status_code}")
        access_token = ok.json()["accessToken"]

        print("\n-- Acceder a /me sin token --")
        anonymous = client.get("/me")
        print(f"GET /me (sin token) -> {anonymous.status_code}")

        print("\n-- Acceder a /me con el token emitido --")
        authenticated = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
        print(f"GET /me (con token) -> {authenticated.status_code}: {authenticated.json()}")
