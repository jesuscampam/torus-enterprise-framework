"""Contratos de autenticación y autorización.

Ver docs/standards/SECURITY-STANDARD.md. ``AuthenticationProvider``/
``AuthorizationProvider`` (Sprint 2.1) son los contratos originales,
deliberadamente mínimos (``credentials``/retorno sin tipar) — se
mantienen sin cambios por compatibilidad. Desde Sprint 2.7 (Enterprise
Security Platform, ver ADR-007) se añaden los contratos alrededor de los
que se diseña la plataforma real: ``IdentityProvider`` es el contrato
principal — Anonymous/API Key/JWT/LDAP/Azure AD son implementaciones
intercambiables de él, nunca la plataforma acoplada a JWT en particular.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from teaf._internal.security.models import (
    AuthenticationCredentials,
    AuthenticationResult,
    Identity,
    Policy,
    Principal,
    TokenPair,
)


class AuthenticationProvider(ABC):
    """Verifica la identidad de un llamante a partir de credenciales."""

    @abstractmethod
    async def authenticate(self, credentials: Any) -> Any:
        """Verifica ``credentials`` y devuelve el principal autenticado.

        Debe lanzar ``teaf._internal.core.exceptions.AuthenticationException``
        si las credenciales son inválidas o han expirado. El tipo de
        ``credentials``/retorno lo define la implementación concreta
        (JWT, API key, etc.) — el contrato no impone un mecanismo.
        """
        ...


class AuthorizationProvider(ABC):
    """Decide si un principal autenticado puede realizar una acción sobre un recurso."""

    @abstractmethod
    async def authorize(self, principal: Any, *, resource: str, action: str) -> bool:
        """``True`` si ``principal`` puede ejecutar ``action`` sobre ``resource``.

        Debe lanzar ``teaf._internal.core.exceptions.AuthorizationException``
        en vez de devolver ``False`` cuando la llamada espera que la
        ausencia de permiso interrumpa el flujo (la elección la hace el
        llamante).
        """
        ...


class IdentityProvider(ABC):
    """Establece la identidad de un llamante a partir de credenciales genéricas.

    El contrato alrededor del que se diseña la plataforma de seguridad
    (Sprint 2.7, ADR-007) — no JWT en particular. Cada mecanismo concreto
    (Anonymous, API Key, JWT, LDAP, Azure AD, y en el futuro OAuth2/OIDC
    genérico, Keycloak, Auth0, Okta, Google, GitHub, SAML) implementa este
    contrato sin que el ``SecurityMiddleware`` ni el Runtime necesiten
    conocer el mecanismo concreto.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identificador estable de este proveedor (p. ej. ``"jwt"``, ``"ldap"``)."""
        ...

    @abstractmethod
    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        """Autentica ``credentials`` y devuelve la identidad resuelta.

        Debe lanzar una subclase de
        ``teaf._internal.core.exceptions.AuthenticationException`` (ver
        ``teaf._internal.security.exceptions``) si las credenciales no son
        válidas para este proveedor.
        """
        ...

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        """``True`` si este proveedor puede intentar autenticar ``credentials``.

        Por defecto compara ``credentials.scheme`` contra ``provider_id`` —
        suficiente para la mayoría de proveedores; uno que necesite lógica
        de enrutamiento más rica (p. ej. distinguir JWT propio de Azure AD
        por el ``iss`` del token) sobrescribe este método.
        """
        return credentials.scheme == self.provider_id


class OAuth2IdentityProvider(IdentityProvider):
    """Contrato preparado (Sprint 2.7, ADR-007) para proveedores OAuth2 no-OIDC.

    Sin implementación concreta todavía — pensado para GitHub/Apple, cuyo
    flujo (authorization code + intercambio por token + endpoint de
    userinfo propietario, sin descubrimiento OIDC estandarizado) no encaja
    en ``OpenIDConnectIdentityProvider``. Ver
    ``teaf._internal.security.identity_providers.oidc`` para el caso OIDC.
    """

    @abstractmethod
    def get_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """URL a la que redirigir al usuario para iniciar el flujo OAuth2."""
        ...

    @abstractmethod
    async def exchange_code(self, *, code: str, redirect_uri: str) -> AuthenticationResult:
        """Intercambia el ``code`` recibido en el callback por una identidad autenticada."""
        ...


class SAMLIdentityProvider(IdentityProvider):
    """Contrato preparado (Sprint 2.7, ADR-007) para SAML 2.0.

    Sin implementación concreta todavía — SAML es un protocolo XML basado
    en *assertions*, genuinamente distinto de OIDC/JWT (no hay JWKS ni
    tokens firmados con JWS); forzarlo a la forma
    ``OpenIDConnectIdentityProvider`` introduciría una abstracción
    incorrecta, de ahí un contrato propio.
    """

    @abstractmethod
    def build_auth_request(self, *, relay_state: str | None = None) -> str:
        """Construye el ``AuthnRequest`` SAML (normalmente codificado para redirección)."""
        ...

    @abstractmethod
    async def consume_assertion(self, saml_response: str) -> AuthenticationResult:
        """Valida la *assertion* SAML recibida del Identity Provider y resuelve la identidad."""
        ...


class TokenProvider(ABC):
    """Emite, verifica, refresca y revoca tokens de sesión (access + refresh)."""

    @abstractmethod
    async def issue(self, identity: Identity, *, tenant_id: str | None = None) -> TokenPair:
        """Emite un nuevo ``TokenPair`` para ``identity``."""
        ...

    @abstractmethod
    async def verify(self, token: str) -> Identity:
        """Verifica ``token`` y devuelve la identidad que representa.

        Debe lanzar ``TokenExpiredException``/``TokenRevokedException``/
        ``TokenException`` (ver ``teaf._internal.security.exceptions``)
        según corresponda.
        """
        ...

    @abstractmethod
    async def refresh(self, refresh_token: str) -> TokenPair:
        """Cambia ``refresh_token`` por un ``TokenPair`` nuevo (rotación)."""
        ...

    @abstractmethod
    async def revoke(self, token: str) -> None:
        """Revoca ``token`` — deja de ser válido aunque no haya expirado todavía."""
        ...


class SessionProvider(ABC):
    """Sesiones con estado del lado servidor — alternativa/complemento a tokens sin estado."""

    @abstractmethod
    async def create(self, identity: Identity) -> str:
        """Crea una sesión para ``identity`` y devuelve su identificador."""
        ...

    @abstractmethod
    async def get(self, session_id: str) -> Identity | None:
        """Devuelve la identidad asociada a ``session_id``, o ``None`` si no existe/expiró."""
        ...

    @abstractmethod
    async def destroy(self, session_id: str) -> None:
        """Termina la sesión ``session_id`` (logout)."""
        ...


class PermissionResolver(ABC):
    """Resuelve el conjunto efectivo de permisos de un ``Principal``."""

    @abstractmethod
    def resolve(self, principal: Principal) -> frozenset[str]:
        """Permisos efectivos de ``principal`` (propios + los que otorgan sus roles)."""
        ...


class RoleResolver(ABC):
    """Resuelve qué roles corresponden a una ``Identity`` (p. ej. a partir de sus grupos)."""

    @abstractmethod
    def resolve(self, identity: Identity) -> frozenset[Any]:
        """Roles (``teaf._internal.providers.security.rbac.Role``) resueltos para ``identity``."""
        ...


class PolicyEvaluator(ABC):
    """Evalúa una ``Policy`` contra un ``Principal``."""

    @abstractmethod
    def evaluate(self, policy: Policy, principal: Principal) -> bool:
        """``True`` si ``principal`` satisface ``policy``."""
        ...


class PasswordHasher(ABC):
    """Hashing y verificación de contraseñas — nunca se compara texto plano."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Devuelve el hash de ``password`` (incluye algoritmo y parámetros, formato PHC)."""
        ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool:
        """``True`` si ``password`` corresponde a ``hashed``."""
        ...

    @abstractmethod
    def needs_rehash(self, hashed: str) -> bool:
        """``True`` si ``hashed`` se generó con parámetros más débiles que los actuales."""
        ...


class CryptoProvider(ABC):
    """Firmas, hashing genérico y gestión de claves — no confundir con ``PasswordHasher``."""

    @abstractmethod
    def sign(self, data: bytes) -> bytes:
        """Firma ``data`` con la clave activa."""
        ...

    @abstractmethod
    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """``True`` si ``signature`` es válida para ``data`` con alguna clave conocida."""
        ...

    @abstractmethod
    def generate_key(self) -> bytes:
        """Genera una clave criptográficamente segura nueva."""
        ...

    @abstractmethod
    def rotate_keys(self) -> None:
        """Promueve una nueva clave activa, conservando la anterior solo para verificar."""
        ...
