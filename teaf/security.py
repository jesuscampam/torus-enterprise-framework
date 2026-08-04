"""``teaf.security`` — la plataforma de seguridad empresarial de TEAF (Sprint 2.7, ADR-007).

Fachada sobre ``teaf/_internal/security/`` (modelo de dominio, proveedores de
identidad, tokens, criptografía, RBAC/políticas) y
``teaf/_internal/contracts/security.py`` (los contratos sobre los que se
diseña todo lo anterior) — un consumidor de TEAF nunca importa
``teaf._internal.security.*`` ni ``teaf._internal.contracts.security``
directamente, solo ``from teaf.security import ...`` (o ``from teaf import
...``, ver ``teaf/__init__.py``).

``IdentityProvider`` es el contrato alrededor del que se diseña toda la
plataforma — nunca JWT en particular. ``JWTProvider``/``ApiKeyProvider``/
``LDAPProvider``/``AzureADProvider`` son las implementaciones concretas de
Sprint 2.7; ``OpenIDConnectProvider``/``OAuth2IdentityProvider``/
``SAMLIdentityProvider`` son las bases genéricas/contratos preparados para
que un futuro Keycloak/Auth0/Okta/Google/GitHub/SAML se añada sin rediseño
(ver ADR-007).

Nota de nomenclatura — ``JWTProvider`` vs ``ApiKeyProvider``: ambos nombres
del Sprint conviven con dos conceptos relacionados pero distintos por
mecanismo:

- Emisión/verificación de credenciales operables por la propia aplicación
  (mintear un JWT tras un login, emitir/revocar/rotar una API Key) — lo que
  este archivo expone como ``JWTProvider`` (alias de ``JWTTokenProvider``) y
  ``ApiKeyProvider`` (mismo nombre que la clase interna, sin alias — ya se
  llama así).
- Resolución de identidad a partir de credenciales entrantes en cada
  petición HTTP (lo que consume ``IdentityProviderRegistry``/
  ``SecurityMiddleware``) — expuesto con su nombre completo,
  ``JWTIdentityProvider``/``ApiKeyIdentityProvider``/``AnonymousIdentityProvider``,
  sin acortar, para no colisionar con lo anterior. LDAP y Azure AD no tienen
  esta dualidad (no "emiten" nada propio, la autenticación *es* el proveedor
  de identidad), de ahí que ``LDAPProvider``/``AzureADProvider`` sean alias
  directos de ``LDAPIdentityProvider``/``AzureADIdentityProvider``.

``SecurityModule`` (el ``ModuleBase`` que empaqueta todo lo anterior para
``Application(modules=[...])``) **no se expone aquí**, mismo criterio que
``DatabaseModule`` (ver docs/public-api/PUBLIC-API.md, sección 6: "ningún
módulo real" se expone desde ``teaf/``) — construir una aplicación segura
con la API pública se hace componiendo estas piezas directamente (ver
``docs/security/SECURITY-ARCHITECTURE.md`` y ``examples/``), no
importando el módulo del framework.
"""

from __future__ import annotations

from teaf._internal.contracts.security import (
    AuthenticationProvider,
    AuthorizationProvider,
    CryptoProvider,
    IdentityProvider,
    OAuth2IdentityProvider,
    PasswordHasher,
    PermissionResolver,
    PolicyEvaluator,
    RoleResolver,
    SAMLIdentityProvider,
    TokenProvider,
)
from teaf._internal.providers.security.rbac import Permission, Role
from teaf._internal.providers.security.security_context import SecurityContext
from teaf._internal.security.authorization.policy_evaluator import DefaultPolicyEvaluator
from teaf._internal.security.authorization.rbac import (
    PrincipalResolver,
    RolePermissionResolver,
    StaticRoleResolver,
)
from teaf._internal.security.crypto.crypto_provider import HmacCryptoProvider
from teaf._internal.security.crypto.password_hasher import (
    Argon2PasswordHasher,
    BcryptPasswordHasher,
)
from teaf._internal.security.decorators import allow_anonymous, authorize
from teaf._internal.security.dependencies import (
    current_claims,
    current_identity,
    current_principal,
    current_security_context,
)
from teaf._internal.security.identity_providers.anonymous import AnonymousIdentityProvider
from teaf._internal.security.identity_providers.api_key import ApiKeyIdentityProvider
from teaf._internal.security.identity_providers.azure_ad import (
    AzureADIdentityProvider as AzureADProvider,
)
from teaf._internal.security.identity_providers.jwt import JWTIdentityProvider
from teaf._internal.security.identity_providers.ldap import LDAPIdentityProvider as LDAPProvider
from teaf._internal.security.identity_providers.oidc import (
    OpenIDConnectIdentityProvider as OpenIDConnectProvider,
)
from teaf._internal.security.identity_providers.registry import IdentityProviderRegistry
from teaf._internal.security.middleware import SecurityMiddleware
from teaf._internal.security.models import (
    ANONYMOUS_IDENTITY,
    ANONYMOUS_PRINCIPAL,
    AuthenticationCredentials,
    AuthenticationResult,
    Claims,
    Identity,
    Policy,
    PolicyRule,
    Principal,
    TokenPair,
)
from teaf._internal.security.tokens.api_key_provider import (
    ApiKeyProvider,
    ApiKeyRecord,
    ApiKeyStore,
    InMemoryApiKeyStore,
)
from teaf._internal.security.tokens.jwt_provider import (
    InMemoryTokenRevocationStore,
    TokenRevocationStore,
)
from teaf._internal.security.tokens.jwt_provider import JWTTokenProvider as JWTProvider

__all__ = [
    # -- Contexto y modelo de dominio (Identity/Principal/Claims/Policy) --------------
    "SecurityContext",
    "Identity",
    "Principal",
    "Claims",
    "Policy",
    "PolicyRule",
    "TokenPair",
    "AuthenticationCredentials",
    "AuthenticationResult",
    "ANONYMOUS_IDENTITY",
    "ANONYMOUS_PRINCIPAL",
    # -- RBAC ---------------------------------------------------------------------------
    "Role",
    "Permission",
    "PermissionResolver",
    "RoleResolver",
    "PolicyEvaluator",
    "StaticRoleResolver",
    "RolePermissionResolver",
    "PrincipalResolver",
    "DefaultPolicyEvaluator",
    # -- Identity Providers: el contrato central + las 5 implementaciones concretas -----
    "IdentityProvider",
    "AnonymousIdentityProvider",
    "JWTIdentityProvider",
    "ApiKeyIdentityProvider",
    "LDAPProvider",
    "AzureADProvider",
    # -- Contratos preparados para futuros proveedores, sin rediseño (ADR-007) ----------
    "OpenIDConnectProvider",
    "OAuth2IdentityProvider",
    "SAMLIdentityProvider",
    # -- Enrutamiento de identidad + middleware ------------------------------------------
    "IdentityProviderRegistry",
    "SecurityMiddleware",
    # -- Tokens JWT -----------------------------------------------------------------------
    "TokenProvider",
    "JWTProvider",
    "TokenRevocationStore",
    "InMemoryTokenRevocationStore",
    # -- API Keys ---------------------------------------------------------------------------
    "ApiKeyProvider",
    "ApiKeyRecord",
    "ApiKeyStore",
    "InMemoryApiKeyStore",
    # -- Autenticación/autorización (contratos originales, Sprint 2.1) --------------------
    "AuthenticationProvider",
    "AuthorizationProvider",
    # -- Contraseñas y criptografía ---------------------------------------------------------
    "PasswordHasher",
    "Argon2PasswordHasher",
    "BcryptPasswordHasher",
    "CryptoProvider",
    "HmacCryptoProvider",
    # -- Decoradores de autorización declarativa ---------------------------------------------
    "authorize",
    "allow_anonymous",
    # -- Dependencias de FastAPI para leer el SecurityContext de la petición ----------------
    "current_identity",
    "current_principal",
    "current_claims",
    "current_security_context",
]
