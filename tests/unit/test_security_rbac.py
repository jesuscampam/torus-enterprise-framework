"""Pruebas de RBAC/políticas: ``StaticRoleResolver``, ``RolePermissionResolver``,
``PrincipalResolver`` y ``DefaultPolicyEvaluator``."""

from __future__ import annotations

from teaf.security import (
    Claims,
    DefaultPolicyEvaluator,
    Identity,
    Policy,
    Principal,
    PrincipalResolver,
    Role,
    RolePermissionResolver,
    StaticRoleResolver,
)


def _identity(**claims_kwargs: object) -> Identity:
    return Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice", **claims_kwargs))  # type: ignore[arg-type]


def test_static_role_resolver_maps_claim_role_names_to_catalog_roles() -> None:
    admin_role = Role(name="admin", permissions=frozenset({"users:delete"}))
    resolver = StaticRoleResolver(roles_by_name={"admin": admin_role})

    resolved = resolver.resolve(_identity(roles=frozenset({"admin"})))
    assert resolved == frozenset({admin_role})


def test_static_role_resolver_ignores_role_names_outside_the_catalog() -> None:
    resolver = StaticRoleResolver(roles_by_name={"admin": Role(name="admin")})
    resolved = resolver.resolve(_identity(roles=frozenset({"unknown-role"})))
    assert resolved == frozenset()


def test_role_permission_resolver_combines_direct_and_role_granted_permissions() -> None:
    role = Role(name="admin", permissions=frozenset({"users:delete"}))
    identity = _identity()
    principal = Principal(
        identity=identity, roles=frozenset({role}), permissions=frozenset({"users:read"})
    )
    resolver = RolePermissionResolver()
    effective = resolver.resolve(principal)
    assert effective == frozenset({"users:read", "users:delete"})


def test_principal_resolver_builds_a_principal_with_effective_permissions() -> None:
    admin_role = Role(name="admin", permissions=frozenset({"users:delete"}))
    role_resolver = StaticRoleResolver(roles_by_name={"admin": admin_role})
    resolver = PrincipalResolver(role_resolver=role_resolver)

    identity = _identity(roles=frozenset({"admin"}), permissions=frozenset({"users:read"}))
    principal = resolver.resolve(identity)

    assert principal.roles == frozenset({admin_role})
    assert principal.permissions == frozenset({"users:read", "users:delete"})
    assert principal.has_role("admin") is True
    assert principal.has_permission("users:delete") is True


def test_principal_resolver_propagates_tenant_from_claims() -> None:
    resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={}))
    identity = _identity(tenant="acme")
    principal = resolver.resolve(identity)
    assert principal.tenant_id == "acme"


def test_default_policy_evaluator_delegates_to_policy_evaluate() -> None:
    identity = _identity(tenant="acme")
    principal = Principal(identity=identity, tenant_id="acme")
    policy = Policy(name="same-tenant", rule=lambda p: p.tenant_id == "acme")

    evaluator = DefaultPolicyEvaluator()
    assert evaluator.evaluate(policy, principal) is True

    other_principal = Principal(identity=identity, tenant_id="other-tenant")
    assert evaluator.evaluate(policy, other_principal) is False
