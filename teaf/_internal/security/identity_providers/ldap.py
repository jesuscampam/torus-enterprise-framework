"""``LDAPIdentityProvider`` — autenticación contra LDAP/Active Directory vía ``ldap3``.

Bind simple con las credenciales del usuario (nunca se guarda ni reenvía
la contraseña más allá del bind), seguido de una búsqueda de sus grupos;
los grupos se convierten a roles y/o permisos según el mapeo configurado
(``group_to_role``/``group_to_permissions``, típicamente poblado desde
``SecuritySettings``). ``ldap3`` es síncrono — cada bind/búsqueda corre en
threadpool (``asyncio.to_thread``) para no bloquear el event loop, ver
ADR-007.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

import ldap3
from ldap3.core.exceptions import LDAPException as Ldap3Exception

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.security.exceptions import LdapException
from teaf._internal.security.models import (
    AuthenticationCredentials,
    AuthenticationResult,
    Claims,
    Identity,
)


class LDAPIdentityProvider(IdentityProvider):
    """Autentica ``username``/``password`` contra un servidor LDAP/Active Directory."""

    def __init__(
        self,
        *,
        server_uri: str,
        base_dn: str,
        user_dn_template: str,
        group_search_base: str | None = None,
        group_search_filter: str = "(member={user_dn})",
        group_to_role: Mapping[str, str] | None = None,
        group_to_permissions: Mapping[str, frozenset[str]] | None = None,
        use_ssl: bool = True,
        connection_factory: type[ldap3.Connection] = ldap3.Connection,
    ) -> None:
        """``user_dn_template`` acepta los placeholders ``{username}``/``{base_dn}``
        (p. ej. ``"uid={username},ou=people,{base_dn}"`` en OpenLDAP, o
        ``"{username}@corp.example.com"`` para bind por UPN en Active Directory).
        ``group_to_role``/``group_to_permissions`` mapean el ``cn`` de cada grupo
        LDAP del usuario a un nombre de rol / conjunto de permisos — ambos
        opcionales y combinables. ``connection_factory`` existe para poder
        inyectar ``ldap3.Connection`` con ``client_strategy=ldap3.MOCK_SYNC`` en
        pruebas, sin un servidor LDAP real."""
        self._server_uri = server_uri
        self._base_dn = base_dn
        self._user_dn_template = user_dn_template
        self._group_search_base = group_search_base or base_dn
        self._group_search_filter = group_search_filter
        self._group_to_role = dict(group_to_role or {})
        self._group_to_permissions = dict(group_to_permissions or {})
        self._use_ssl = use_ssl
        self._connection_factory = connection_factory

    @property
    def provider_id(self) -> str:
        return "ldap"

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Bind + búsqueda de grupos, ejecutados en threadpool (``ldap3`` es síncrono)."""
        if not credentials.username or not credentials.password:
            raise LdapException("Faltan usuario/contraseña (scheme 'ldap').")
        return await asyncio.to_thread(
            self._authenticate_sync, credentials.username, credentials.password
        )

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        return (
            credentials.scheme == self.provider_id
            and credentials.username is not None
            and credentials.password is not None
        )

    def _build_server(self) -> ldap3.Server:
        return ldap3.Server(self._server_uri, use_ssl=self._use_ssl, get_info=ldap3.NONE)

    def _authenticate_sync(self, username: str, password: str) -> AuthenticationResult:
        user_dn = self._user_dn_template.format(username=username, base_dn=self._base_dn)
        try:
            connection = self._connection_factory(
                self._build_server(), user=user_dn, password=password, auto_bind=True
            )
        except Ldap3Exception as exc:
            raise LdapException(f"Bind LDAP fallido para '{username}': {exc}") from exc

        try:
            groups = self._search_groups(connection, user_dn)
        finally:
            connection.unbind()

        roles = frozenset(
            self._group_to_role[group] for group in groups if group in self._group_to_role
        )
        permissions: set[str] = set()
        for group in groups:
            permissions.update(self._group_to_permissions.get(group, frozenset()))

        claims = Claims(
            sub=username,
            roles=roles,
            permissions=frozenset(permissions),
            groups=frozenset(groups),
        )
        identity = Identity(id=username, provider_id=self.provider_id, claims=claims)
        return AuthenticationResult(identity=identity)

    def _search_groups(self, connection: ldap3.Connection, user_dn: str) -> tuple[str, ...]:
        search_filter = self._group_search_filter.format(user_dn=user_dn)
        try:
            connection.search(self._group_search_base, search_filter, attributes=["cn"])
        except Ldap3Exception as exc:
            raise LdapException(f"Búsqueda de grupos LDAP fallida: {exc}") from exc

        groups: list[str] = []
        for entry in connection.entries:
            cn_values = entry.entry_attributes_as_dict.get("cn")
            if cn_values:
                groups.append(str(cn_values[0]))
        return tuple(groups)
