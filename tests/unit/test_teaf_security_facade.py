"""Pruebas de la fachada pública ``teaf.security`` (Sprint 2.7, ADR-007).

Mismo criterio que ``tests/unit/test_teaf_package.py``: la superficie pública
es intencional, no accidental — se verifica de forma explícita, no se infiere.
"""

from __future__ import annotations

import teaf
import teaf.security

_EXPECTED_ALL = {
    "ANONYMOUS_IDENTITY",
    "ANONYMOUS_PRINCIPAL",
    "AnonymousIdentityProvider",
    "ApiKeyIdentityProvider",
    "ApiKeyProvider",
    "ApiKeyRecord",
    "ApiKeyStore",
    "Argon2PasswordHasher",
    "AuthenticationCredentials",
    "AuthenticationProvider",
    "AuthenticationResult",
    "AuthorizationProvider",
    "AzureADProvider",
    "BcryptPasswordHasher",
    "Claims",
    "CryptoProvider",
    "DefaultPolicyEvaluator",
    "HmacCryptoProvider",
    "Identity",
    "IdentityProvider",
    "IdentityProviderRegistry",
    "InMemoryApiKeyStore",
    "InMemoryTokenRevocationStore",
    "JWTIdentityProvider",
    "JWTProvider",
    "LDAPProvider",
    "OAuth2IdentityProvider",
    "OpenIDConnectProvider",
    "PasswordHasher",
    "Permission",
    "PermissionResolver",
    "Policy",
    "PolicyEvaluator",
    "PolicyRule",
    "Principal",
    "PrincipalResolver",
    "Role",
    "RolePermissionResolver",
    "RoleResolver",
    "SAMLIdentityProvider",
    "SecurityContext",
    "SecurityMiddleware",
    "StaticRoleResolver",
    "TokenPair",
    "TokenProvider",
    "TokenRevocationStore",
    "allow_anonymous",
    "authorize",
    "current_claims",
    "current_identity",
    "current_principal",
    "current_security_context",
}


def test_all_is_defined_explicitly() -> None:
    assert hasattr(teaf.security, "__all__")
    assert isinstance(teaf.security.__all__, list)


def test_all_matches_the_expected_public_surface_exactly() -> None:
    assert set(teaf.security.__all__) == _EXPECTED_ALL


def test_all_has_no_duplicates() -> None:
    assert len(teaf.security.__all__) == len(set(teaf.security.__all__))


def test_every_symbol_in_all_is_actually_importable() -> None:
    for name in teaf.security.__all__:
        assert hasattr(teaf.security, name), f"'{name}' está en __all__ pero no es un atributo"


def test_every_security_symbol_is_also_reexported_from_top_level_teaf() -> None:
    """``from teaf import SecurityContext`` funciona igual que ``from teaf.security import ...``
    — ver la nota de Sprint 2.7 en el docstring de ``teaf/__init__.py``."""
    for name in _EXPECTED_ALL:
        assert hasattr(teaf, name), f"'{name}' no se reexporta desde 'teaf' de nivel superior"
        assert getattr(teaf, name) is getattr(teaf.security, name)


def test_security_module_is_not_exposed_from_the_public_facade() -> None:
    """``SecurityModule`` se queda privado — mismo criterio que ``DatabaseModule``
    (ver docs/public-api/PUBLIC-API.md, sección 6)."""
    assert "SecurityModule" not in teaf.security.__all__
    assert not hasattr(teaf.security, "SecurityModule")
    assert not hasattr(teaf, "SecurityModule")


def test_jwt_provider_is_the_token_issuer_not_the_identity_provider_adapter() -> None:
    """Ver la nota de nomenclatura en el docstring de ``teaf/security.py``:
    ``JWTProvider`` emite/verifica/refresca/revoca tokens; ``JWTIdentityProvider``
    (expuesto por separado, sin acortar) resuelve identidad en cada petición."""
    from teaf._internal.security.tokens.jwt_provider import JWTTokenProvider

    assert teaf.security.JWTProvider is JWTTokenProvider


def test_ldap_and_azure_ad_providers_are_the_identity_provider_implementations() -> None:
    from teaf._internal.security.identity_providers.azure_ad import AzureADIdentityProvider
    from teaf._internal.security.identity_providers.ldap import LDAPIdentityProvider

    assert teaf.security.LDAPProvider is LDAPIdentityProvider
    assert teaf.security.AzureADProvider is AzureADIdentityProvider


def test_open_id_connect_provider_is_the_generic_oidc_base_class() -> None:
    from teaf._internal.security.identity_providers.oidc import OpenIDConnectIdentityProvider

    assert teaf.security.OpenIDConnectProvider is OpenIDConnectIdentityProvider
    assert issubclass(teaf.security.AzureADProvider, teaf.security.OpenIDConnectProvider)
