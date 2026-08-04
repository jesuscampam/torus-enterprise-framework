"""Pruebas del modelo de dominio de seguridad (Claims, Identity, Principal, Policy, TokenPair)."""

from __future__ import annotations

from teaf.security import (
    ANONYMOUS_IDENTITY,
    ANONYMOUS_PRINCIPAL,
    Claims,
    Identity,
    Policy,
    Principal,
    Role,
    TokenPair,
)


def test_claims_defaults_to_only_sub_required() -> None:
    claims = Claims(sub="alice")
    assert claims.sub == "alice"
    assert claims.name is None
    assert claims.roles == frozenset()
    assert claims.extra == {}


def test_claims_as_dict_is_serializable() -> None:
    claims = Claims(sub="alice", roles=frozenset({"admin"}), permissions=frozenset({"read"}))
    payload = claims.as_dict()
    assert payload["sub"] == "alice"
    assert payload["roles"] == ["admin"]
    assert payload["permissions"] == ["read"]


def test_identity_name_is_a_shortcut_to_claims_name() -> None:
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice", name="Alice"))
    assert identity.name == "Alice"


def test_anonymous_identity_is_not_authenticated() -> None:
    assert ANONYMOUS_IDENTITY.authenticated is False
    assert ANONYMOUS_IDENTITY.id == "anonymous"


def test_principal_id_and_is_authenticated_shortcuts() -> None:
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice"))
    principal = Principal(identity=identity)
    assert principal.id == "alice"
    assert principal.is_authenticated is True


def test_anonymous_principal_is_not_authenticated_and_has_no_roles() -> None:
    assert ANONYMOUS_PRINCIPAL.is_authenticated is False
    assert ANONYMOUS_PRINCIPAL.roles == frozenset()
    assert ANONYMOUS_PRINCIPAL.permissions == frozenset()


def test_principal_has_role_checks_role_names() -> None:
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice"))
    principal = Principal(identity=identity, roles=frozenset({Role(name="admin")}))
    assert principal.has_role("admin") is True
    assert principal.has_role("viewer") is False


def test_principal_has_permission_checks_direct_and_role_granted_permissions() -> None:
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice"))
    role = Role(name="admin", permissions=frozenset({"users:delete"}))
    principal = Principal(
        identity=identity, roles=frozenset({role}), permissions=frozenset({"users:read"})
    )
    assert principal.has_permission("users:read") is True
    assert principal.has_permission("users:delete") is True
    assert principal.has_permission("users:create") is False


def test_policy_evaluate_delegates_to_rule() -> None:
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice", tenant="acme"))
    principal = Principal(identity=identity, tenant_id="acme")
    policy = Policy(name="same-tenant", rule=lambda p: p.tenant_id == "acme")
    assert policy.evaluate(principal) is True

    other = Principal(identity=identity, tenant_id="other")
    assert policy.evaluate(other) is False


def test_token_pair_as_dict_is_serializable() -> None:
    pair = TokenPair(access_token="a", refresh_token="b", expires_in=900)
    payload = pair.as_dict()
    assert payload == {
        "accessToken": "a",
        "refreshToken": "b",
        "tokenType": "Bearer",
        "expiresIn": 900,
    }
