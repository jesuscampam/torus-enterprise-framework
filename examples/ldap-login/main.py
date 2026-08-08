"""LDAP Login — autenticar contra Active Directory/LDAP y convertir grupos en roles.

Demuestra ``LDAPProvider``: bind con usuario/contraseña, búsqueda de sus
grupos LDAP y su conversión a roles/permisos (``group_to_role``/
``group_to_permissions``), sin guardar ni reenviar la contraseña más allá
del bind.

Este ejemplo usa un servidor LDAP falso (``connection_factory``, el mismo
parámetro de extensibilidad que expone ``LDAPProvider`` para pruebas) para
poder ejecutarse sin un Active Directory real disponible — en producción
se omite ``connection_factory`` y ``LDAPProvider`` usa ``ldap3.Connection``
contra ``server_uri`` de verdad.

Ejecutar:

    python examples/ldap-login/main.py
"""

from __future__ import annotations

import base64

from fastapi import Depends
from fastapi.testclient import TestClient
from ldap3.core.exceptions import LDAPBindError
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider,
    IdentityProviderRegistry,
    LDAPProvider,
    Principal,
    PrincipalResolver,
    Role,
    SecurityMiddleware,
    StaticRoleResolver,
    authorize,
    current_principal,
)


class _FakeLdapEntry:
    def __init__(self, cn: str) -> None:
        self.entry_attributes_as_dict = {"cn": [cn]}


class _FakeLdapConnection:
    """Sustituto de ``ldap3.Connection`` — solo para que este ejemplo corra sin un
    servidor LDAP real. Ver ``LDAPProvider(connection_factory=...)``."""

    _DIRECTORY = {"cn=alice,dc=corp,dc=example,dc=com": "correct-password"}
    _GROUPS = {"cn=alice,dc=corp,dc=example,dc=com": ("network-admins",)}

    def __init__(self, server: object, user: str, password: str, auto_bind: bool) -> None:
        if self._DIRECTORY.get(user) != password:
            raise LDAPBindError(f"Bind LDAP fallido para '{user}'.")
        self._user = user
        self.entries: list[_FakeLdapEntry] = []

    def search(self, base: str, search_filter: str, attributes: list[str]) -> None:
        self.entries = [_FakeLdapEntry(cn) for cn in self._GROUPS.get(self._user, ())]

    def unbind(self) -> None:
        pass


ldap_provider = LDAPProvider(
    server_uri="ldaps://corp.example.com",
    base_dn="dc=corp,dc=example,dc=com",
    user_dn_template="cn={username},{base_dn}",
    group_to_role={"network-admins": "admin"},
    group_to_permissions={"network-admins": frozenset({"tickets:close"})},
    connection_factory=_FakeLdapConnection,  # type: ignore[arg-type]
)

provider_registry = IdentityProviderRegistry([AnonymousIdentityProvider(), ldap_provider])
role_resolver = StaticRoleResolver(
    roles_by_name={"admin": Role(name="admin", permissions=frozenset({"tickets:close"}))}
)
principal_resolver = PrincipalResolver(role_resolver=role_resolver)

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)


@app.asgi.get("/tickets/close")
@authorize(role="admin")
def close_ticket(principal: Principal = Depends(current_principal)) -> dict[str, object]:
    return {"closedBy": principal.id}


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


if __name__ == "__main__":
    with TestClient(app.asgi) as client:
        print("-- Bind con contraseña incorrecta --")
        wrong = client.get("/tickets/close", headers=_basic_auth_header("alice", "wrong"))
        print(f"GET /tickets/close (bind fallido) -> {wrong.status_code}")

        print("\n-- Bind correcto, grupo LDAP mapeado a rol 'admin' --")
        right = client.get(
            "/tickets/close", headers=_basic_auth_header("alice", "correct-password")
        )
        print(f"GET /tickets/close (bind correcto) -> {right.status_code}: {right.json()}")
