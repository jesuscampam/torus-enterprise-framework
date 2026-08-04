"""RBAC por defecto: ``RoleResolver``, ``PermissionResolver`` y ``PrincipalResolver``.

Reutiliza ``Role``/``Permission`` de
``teaf/_internal/providers/security/rbac.py`` (Sprint 2.2) — este módulo
no redefine el modelo de rol, solo aporta cómo se *resuelve* (de nombres
de rol/grupos crudos en una ``Identity`` a objetos ``Role`` con permisos
concretos, y de ahí a un ``Principal`` listo para autorizar).
"""

from __future__ import annotations

from collections.abc import Mapping

from teaf._internal.contracts.security import PermissionResolver, RoleResolver
from teaf._internal.providers.security.rbac import Permission, Role
from teaf._internal.security.models import Identity, Principal


class StaticRoleResolver(RoleResolver):
    """Resuelve roles a partir de un catálogo fijo ``nombre de rol -> Role``.

    Cruza ``identity.claims.roles`` (nombres de rol que ya trae la
    identidad — p. ej. un JWT propio donde el emisor decide roles
    directamente) contra el catálogo; los nombres sin entrada en el
    catálogo se ignoran silenciosamente (una identidad puede traer roles
    que esta aplicación no reconoce).
    """

    def __init__(self, *, roles_by_name: Mapping[str, Role]) -> None:
        self._roles_by_name = dict(roles_by_name)

    def resolve(self, identity: Identity) -> frozenset[Role]:
        return frozenset(
            self._roles_by_name[name]
            for name in identity.claims.roles
            if name in self._roles_by_name
        )


class RolePermissionResolver(PermissionResolver):
    """Permisos efectivos = permisos directos del ``Principal`` + los que otorgan sus roles."""

    def resolve(self, principal: Principal) -> frozenset[Permission]:
        permissions: set[Permission] = set(principal.permissions)
        for role in principal.roles:
            permissions.update(role.permissions)
        return frozenset(permissions)


class PrincipalResolver:
    """Construye un ``Principal`` completo a partir de una ``Identity`` autenticada.

    Combina ``RoleResolver`` (nombres de rol → ``Role`` con permisos) y
    ``PermissionResolver`` (roles + permisos directos → permisos
    efectivos) — el paso que ``SecurityMiddleware`` ejecuta justo después
    de que un ``IdentityProvider`` autentica, antes de publicar el
    ``SecurityContext`` de la petición.
    """

    def __init__(
        self,
        *,
        role_resolver: RoleResolver,
        permission_resolver: PermissionResolver | None = None,
    ) -> None:
        self._role_resolver = role_resolver
        self._permission_resolver = permission_resolver or RolePermissionResolver()

    def resolve(self, identity: Identity) -> Principal:
        """Roles + permisos directos de ``identity`` → ``Principal`` con permisos efectivos."""
        roles = self._role_resolver.resolve(identity)
        principal_with_roles = Principal(
            identity=identity,
            roles=roles,
            permissions=frozenset(identity.claims.permissions),
            tenant_id=identity.claims.tenant,
        )
        effective_permissions = self._permission_resolver.resolve(principal_with_roles)
        return Principal(
            identity=identity,
            roles=roles,
            permissions=effective_permissions,
            tenant_id=identity.claims.tenant,
        )
