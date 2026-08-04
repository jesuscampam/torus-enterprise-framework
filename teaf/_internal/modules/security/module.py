"""``SecurityModule`` — el módulo oficial de seguridad de TEAF, sobre el Module SDK.

Mismo patrón que ``DatabaseModule`` (Sprint 2.6): todo lo concreto
(``TokenProvider``, ``ApiKeyProvider``, ``PasswordHasher``,
``CryptoProvider``, el catálogo de roles, el registro de Identity
Providers) se construye en ``__init__`` — no en ``initialize()`` — porque
``ModuleBase.bootstrap()`` llama a ``get_manifest()`` **antes** de
ejecutar cualquier hook del ciclo de vida, y el manifiesto necesita esas
instancias ya construidas para declarar sus servicios.

``provider_registry``/``principal_resolver`` quedan disponibles como
atributos públicos inmediatamente después de construir el módulo —
**antes** de pasarlo a ``Application(modules=[...])`` — porque
``SecurityMiddleware`` los necesita para configurarse, y el middleware
debe añadirse antes de que arranque el ciclo de vida de la aplicación
(ver docs/security/SECURITY-ARCHITECTURE.md, "Cómo conectarlo").
"""

from __future__ import annotations

from collections.abc import Sequence

from teaf._internal.contracts.security import IdentityProvider
from teaf._internal.modules.security.configuration import SecurityConfiguration
from teaf._internal.modules.security.health import SecurityHealth
from teaf._internal.modules.security.manifest import build_security_manifest
from teaf._internal.providers.security.rbac import Role
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase
from teaf._internal.security.authorization.rbac import PrincipalResolver, StaticRoleResolver
from teaf._internal.security.crypto.crypto_provider import HmacCryptoProvider
from teaf._internal.security.crypto.password_hasher import (
    Argon2PasswordHasher,
    BcryptPasswordHasher,
)
from teaf._internal.security.identity_providers.anonymous import AnonymousIdentityProvider
from teaf._internal.security.identity_providers.api_key import ApiKeyIdentityProvider
from teaf._internal.security.identity_providers.jwt import JWTIdentityProvider
from teaf._internal.security.identity_providers.registry import IdentityProviderRegistry
from teaf._internal.security.tokens.api_key_provider import ApiKeyProvider
from teaf._internal.security.tokens.jwt_provider import JWTTokenProvider


class SecurityModule(ModuleBase):
    """Plataforma de seguridad: Identity Providers, RBAC, tokens y criptografía."""

    def __init__(
        self,
        configuration: SecurityConfiguration | None = None,
        *,
        identity_providers: Sequence[IdentityProvider] = (),
    ) -> None:
        """``identity_providers`` es donde se pasan proveedores que necesitan
        configuración específica del entorno que no tiene sentido "adivinar"
        (``LDAPIdentityProvider``, ``AzureADIdentityProvider``, o uno propio) —
        Anonymous/API Key/JWT siempre se construyen automáticamente, esos tres
        nunca necesitan pasarse a mano."""
        super().__init__()
        self.configuration = configuration or SecurityConfiguration()

        self.token_provider = JWTTokenProvider(
            secret=self.configuration.jwt_secret,
            algorithm=self.configuration.jwt_algorithm,
            issuer=self.configuration.jwt_issuer,
            audience=self.configuration.jwt_audience,
            access_token_ttl_seconds=self.configuration.access_token_ttl_seconds,
            refresh_token_ttl_seconds=self.configuration.refresh_token_ttl_seconds,
            clock_skew_seconds=self.configuration.clock_skew_seconds,
        )
        self.api_key_provider = ApiKeyProvider(
            secret=self.configuration.api_key_hash_secret or self.configuration.jwt_secret,
        )

        password_hasher_cls = (
            BcryptPasswordHasher
            if self.configuration.password_hasher == "bcrypt"
            else Argon2PasswordHasher
        )
        self.password_hasher = password_hasher_cls()
        self.crypto_provider = HmacCryptoProvider(
            secret_keys=(self.configuration.jwt_secret.encode("utf-8"),)
        )

        roles_by_name = {
            name: Role(name=name, permissions=frozenset(permissions))
            for name, permissions in self.configuration.roles.items()
        }
        self.role_resolver = StaticRoleResolver(roles_by_name=roles_by_name)
        self.principal_resolver = PrincipalResolver(role_resolver=self.role_resolver)

        self.provider_registry = IdentityProviderRegistry(
            [
                AnonymousIdentityProvider(),
                JWTIdentityProvider(token_provider=self.token_provider),
                ApiKeyIdentityProvider(api_key_provider=self.api_key_provider),
                *identity_providers,
            ]
        )

        self.health = SecurityHealth(self.provider_registry)

    def get_manifest(self) -> ModuleManifest:
        return build_security_manifest(
            self.configuration,
            provider_registry=self.provider_registry,
            password_hasher=self.password_hasher,
            crypto_provider=self.crypto_provider,
            health=self.health,
        )

    async def start(self, context: ModuleContext) -> None:
        """Refresca la caché de salud — sin I/O de red que abrir (JWT/API Key son en memoria)."""
        await self.health.refresh()

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info(
            "security_module_ready",
            extra={
                "context": {"providers": [p.provider_id for p in self.provider_registry.providers]}
            },
        )

    async def dispose(self, context: ModuleContext) -> None:
        """Libera recursos de los proveedores que los tengan (p. ej. ``httpx.AsyncClient``
        de los proveedores OIDC) — vía duck typing (``aclose()``), sin que este módulo
        necesite conocer qué proveedores concretos están registrados."""
        for provider in self.provider_registry.providers:
            aclose = getattr(provider, "aclose", None)
            if aclose is not None:
                await aclose()
