"""``build_security_manifest`` — el ``ModuleManifest`` del Security Module.

Separado de ``SecurityModule`` (``module.py``) a propósito, mismo criterio
que ``modules/database/manifest.py``: aquí solo se *describe* el módulo —
nada se registra contra ningún ``Runtime`` desde este archivo, eso lo hace
el SDK durante ``ModuleBase.bootstrap()``.
"""

from __future__ import annotations

from teaf._internal.contracts.security import CryptoProvider, PasswordHasher
from teaf._internal.modules.security.configuration import SecurityConfiguration
from teaf._internal.modules.security.health import SecurityHealth
from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.security.identity_providers.registry import IdentityProviderRegistry


def build_security_manifest(
    configuration: SecurityConfiguration,
    *,
    provider_registry: IdentityProviderRegistry,
    password_hasher: PasswordHasher,
    crypto_provider: CryptoProvider,
    health: SecurityHealth,
) -> ModuleManifest:
    """Construye el manifiesto del Security Module sobre instancias ya construidas.

    ``provider_registry``/``password_hasher``/``crypto_provider``/``health``
    se construyen en ``SecurityModule.__init__`` (antes de que
    ``bootstrap()`` llame a ``get_manifest()`` por primera vez) — este
    builder solo los declara, nunca los crea.
    """
    return (
        ModuleBuilder(id="security", name="security", display_name="Security")
        .with_version("1.0.0")
        .with_description(
            "Plataforma de seguridad empresarial de TEAF: Identity Providers "
            "(Anonymous, API Key, JWT, LDAP, Azure AD), RBAC, políticas, tokens y criptografía."
        )
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.SECURITY)
        .with_tags("authentication", "authorization", "jwt", "rbac", "identity")
        .with_documentation("docs/security/SECURITY-ARCHITECTURE.md")
        .with_runtime_compatibility(">=0.6.0")
        .with_sdk_compatibility(">=1.0.0")
        .add_capability(
            id="security",
            name="security",
            category=CapabilityCategory.SECURITY,
            description="Plataforma de seguridad — capacidad general del módulo.",
        )
        .add_capability(
            id="security.authentication",
            name="security-authentication",
            category=CapabilityCategory.SECURITY,
            description="Resolución de identidad vía Identity Providers intercambiables.",
        )
        .add_capability(
            id="security.authorization",
            name="security-authorization",
            category=CapabilityCategory.SECURITY,
            description="RBAC (roles/permisos) y políticas de autorización.",
        )
        .add_capability(
            id="security.tokens",
            name="security-tokens",
            category=CapabilityCategory.SECURITY,
            description="Emisión, verificación, refresco y revocación de JWT y API Keys.",
        )
        .add_capability(
            id="security.crypto",
            name="security-crypto",
            category=CapabilityCategory.SECURITY,
            description="Hashing de contraseñas (Argon2id/BCrypt) y firmas HMAC.",
        )
        .add_configuration(
            key="jwt_secret",
            description="Secreto (HS256) o clave privada PEM (RS256/ES256) para firmar JWT.",
            required=True,
            sensitive=True,
        )
        .add_configuration(
            key="jwt_algorithm",
            description="Algoritmo de firma JWT.",
            default=configuration.jwt_algorithm,
        )
        .add_configuration(
            key="access_token_ttl_seconds",
            description="Vida del access token, en segundos.",
            default=configuration.access_token_ttl_seconds,
        )
        .add_configuration(
            key="refresh_token_ttl_seconds",
            description="Vida del refresh token, en segundos.",
            default=configuration.refresh_token_ttl_seconds,
        )
        .add_configuration(
            key="password_hasher",
            description="'argon2' (por defecto) o 'bcrypt'.",
            default=configuration.password_hasher,
        )
        .add_service(
            IdentityProviderRegistry,
            lambda c: provider_registry,
            lifetime=Lifetime.SINGLETON,
            description="Registro de Identity Providers (Anonymous/API Key/JWT/LDAP/Azure AD/...).",
            capabilities=("security.authentication",),
        )
        .add_service(
            PasswordHasher,
            lambda c: password_hasher,
            lifetime=Lifetime.SINGLETON,
            description="Hashing y verificación de contraseñas.",
            capabilities=("security.crypto",),
        )
        .add_service(
            CryptoProvider,
            lambda c: crypto_provider,
            lifetime=Lifetime.SINGLETON,
            description="Firmas HMAC-SHA256 con rotación de claves.",
            capabilities=("security.crypto",),
        )
        .add_healthcheck(
            name="security.ping",
            description="Al menos un Identity Provider registrado.",
            check=health.check,
        )
        .add_event("authentication.started")
        .add_event("authentication.succeeded")
        .add_event("authentication.failed")
        .add_event("authorization.started")
        .add_event("authorization.succeeded")
        .add_event("authorization.failed")
        .add_event("token.created")
        .add_event("token.refreshed")
        .add_event("token.revoked")
        .add_event("apikey.validated")
        .add_event("ldap.login")
        .add_event("azuread.login")
        .build()
    )
