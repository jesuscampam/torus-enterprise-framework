"""Pruebas de los 5 Identity Providers (Anonymous/JWT/API Key/LDAP) y del registro.

Azure AD (OIDC) se prueba aparte en ``tests/integration/test_security_oidc_azure_ad.py``
— necesita ``httpx.MockTransport`` en vez de fixtures síncronas simples.
"""

from __future__ import annotations

import asyncio

import ldap3
import pytest
from ldap3.core.exceptions import LDAPBindError
from teaf.security import (
    AnonymousIdentityProvider,
    ApiKeyIdentityProvider,
    ApiKeyProvider,
    AuthenticationCredentials,
    Claims,
    Identity,
    IdentityProviderRegistry,
    JWTIdentityProvider,
    JWTProvider,
    LDAPProvider,
)

# -- AnonymousIdentityProvider ----------------------------------------------------------


def test_anonymous_provider_id_is_anonymous() -> None:
    provider = AnonymousIdentityProvider()
    assert provider.provider_id == "anonymous"


def test_anonymous_provider_authenticates_anything_as_the_anonymous_identity() -> None:
    provider = AnonymousIdentityProvider()
    result = asyncio.run(provider.authenticate(AuthenticationCredentials(scheme="anonymous")))
    assert result.identity.authenticated is False
    assert result.identity.id == "anonymous"


def test_anonymous_provider_supports_is_always_true_as_the_fallback_provider() -> None:
    provider = AnonymousIdentityProvider()
    assert provider.supports(AuthenticationCredentials(scheme="anonymous")) is True
    assert provider.supports(AuthenticationCredentials(scheme="jwt")) is True


# -- JWTIdentityProvider -------------------------------------------------------------------


def test_jwt_identity_provider_delegates_verification_to_the_token_provider() -> None:
    token_provider = JWTProvider(secret="test-secret")
    provider = JWTIdentityProvider(token_provider=token_provider)
    identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice"))
    pair = asyncio.run(token_provider.issue(identity))

    result = asyncio.run(
        provider.authenticate(AuthenticationCredentials(scheme="jwt", token=pair.access_token))
    )
    assert result.identity.id == "alice"


def test_jwt_identity_provider_supports_requires_a_token() -> None:
    provider = JWTIdentityProvider(token_provider=JWTProvider(secret="test-secret"))
    assert provider.supports(AuthenticationCredentials(scheme="jwt", token="x")) is True
    assert provider.supports(AuthenticationCredentials(scheme="jwt")) is False


# -- ApiKeyIdentityProvider -----------------------------------------------------------------


def test_api_key_identity_provider_maps_scopes_to_claims_permissions() -> None:
    api_key_provider = ApiKeyProvider(secret="pepper")
    provider = ApiKeyIdentityProvider(api_key_provider=api_key_provider)
    raw_key, _ = api_key_provider.issue(principal_id="bob", scopes=frozenset({"users:read"}))

    result = asyncio.run(
        provider.authenticate(AuthenticationCredentials(scheme="api-key", api_key=raw_key))
    )
    assert result.identity.id == "bob"
    assert result.identity.claims.permissions == frozenset({"users:read"})


# -- LDAPIdentityProvider (conexión falsa, sin servidor LDAP real) ---------------------------


class _FakeEntry:
    def __init__(self, cn: str) -> None:
        self.entry_attributes_as_dict = {"cn": [cn]}


class _FakeConnection:
    """Sustituto mínimo de ``ldap3.Connection`` — ver ``connection_factory`` en ``ldap.py``."""

    _VALID_PASSWORDS = {"cn=alice,dc=example,dc=com": "correct-password"}
    _GROUPS_BY_USER = {"cn=alice,dc=example,dc=com": ("admins",)}

    def __init__(self, server: object, user: str, password: str, auto_bind: bool) -> None:
        if self._VALID_PASSWORDS.get(user) != password:
            raise LDAPBindError(f"Bind inválido para {user}")
        self._user = user
        self.entries: list[_FakeEntry] = []

    def search(self, base: str, search_filter: str, attributes: list[str]) -> None:
        self.entries = [_FakeEntry(cn) for cn in self._GROUPS_BY_USER.get(self._user, ())]

    def unbind(self) -> None:
        pass


def _ldap_provider() -> LDAPProvider:
    return LDAPProvider(
        server_uri="ldap://example.com",
        base_dn="dc=example,dc=com",
        user_dn_template="cn={username},{base_dn}",
        group_to_role={"admins": "admin"},
        group_to_permissions={"admins": frozenset({"users:delete"})},
        connection_factory=_FakeConnection,  # type: ignore[arg-type]
    )


def test_ldap_provider_id_is_ldap() -> None:
    assert _ldap_provider().provider_id == "ldap"


def test_ldap_authenticate_succeeds_with_correct_credentials_and_maps_groups() -> None:
    provider = _ldap_provider()
    result = asyncio.run(
        provider.authenticate(
            AuthenticationCredentials(scheme="ldap", username="alice", password="correct-password")
        )
    )
    assert result.identity.id == "alice"
    assert result.identity.claims.roles == frozenset({"admin"})
    assert result.identity.claims.permissions == frozenset({"users:delete"})
    assert result.identity.claims.groups == frozenset({"admins"})


def test_ldap_authenticate_fails_with_wrong_password() -> None:
    from teaf._internal.security.exceptions import LdapException

    provider = _ldap_provider()
    with pytest.raises(LdapException):
        asyncio.run(
            provider.authenticate(
                AuthenticationCredentials(scheme="ldap", username="alice", password="wrong")
            )
        )


def test_ldap_authenticate_requires_username_and_password() -> None:
    from teaf._internal.security.exceptions import LdapException

    provider = _ldap_provider()
    with pytest.raises(LdapException):
        asyncio.run(provider.authenticate(AuthenticationCredentials(scheme="ldap")))


def test_ldap_provider_default_connection_factory_is_ldap3_connection() -> None:
    """El valor por defecto de ``connection_factory`` sigue siendo ``ldap3.Connection``
    — la inyección de ``_FakeConnection`` es solo para pruebas."""
    provider = LDAPProvider(
        server_uri="ldap://example.com",
        base_dn="dc=example,dc=com",
        user_dn_template="cn={username},{base_dn}",
    )
    assert provider._connection_factory is ldap3.Connection  # type: ignore[attr-defined]


# -- IdentityProviderRegistry ----------------------------------------------------------------


def test_registry_resolves_by_exact_scheme_match() -> None:
    jwt_provider = JWTIdentityProvider(token_provider=JWTProvider(secret="test-secret"))
    registry = IdentityProviderRegistry([AnonymousIdentityProvider(), jwt_provider])

    resolved = registry.resolve(AuthenticationCredentials(scheme="jwt", token="x"))
    assert resolved is jwt_provider


def test_registry_resolve_returns_none_when_nothing_matches_without_fallback() -> None:
    jwt_provider = JWTIdentityProvider(token_provider=JWTProvider(secret="test-secret"))
    registry = IdentityProviderRegistry([jwt_provider])
    resolved = registry.resolve(
        AuthenticationCredentials(scheme="ldap", username="a", password="b")
    )
    assert resolved is None


def test_registry_resolve_falls_back_to_anonymous_when_registered() -> None:
    anonymous = AnonymousIdentityProvider()
    registry = IdentityProviderRegistry([anonymous])
    resolved = registry.resolve(
        AuthenticationCredentials(scheme="ldap", username="a", password="b")
    )
    assert resolved is anonymous


def test_registry_register_and_unregister() -> None:
    registry = IdentityProviderRegistry()
    provider = AnonymousIdentityProvider()

    registry.register(provider)
    assert registry.get("anonymous") is provider

    registry.unregister("anonymous")
    assert registry.get("anonymous") is None


def test_registry_unregister_of_unknown_provider_does_not_raise() -> None:
    registry = IdentityProviderRegistry()
    registry.unregister("does-not-exist")  # no debe lanzar


def test_registry_providers_property_lists_all_in_registration_order() -> None:
    anonymous = AnonymousIdentityProvider()
    jwt_provider = JWTIdentityProvider(token_provider=JWTProvider(secret="test-secret"))
    registry = IdentityProviderRegistry([anonymous, jwt_provider])
    assert registry.providers == (anonymous, jwt_provider)
