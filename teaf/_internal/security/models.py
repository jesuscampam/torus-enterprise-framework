"""Modelo de dominio de la plataforma de seguridad (Identity, Principal, Claims, Policy).

Reutiliza `Role`/`Permission` de `teaf/_internal/providers/security/rbac.py`
(Sprint 2.2) en vez de duplicarlos — este módulo añade las piezas que
faltaban por encima: qué es un llamante autenticado (`Identity`), qué
credenciales recibe un `IdentityProvider` y qué produce
(`AuthenticationCredentials`/`AuthenticationResult`), y el sujeto de
autorización ya resuelto (`Principal`, con roles/permisos/tenant).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from teaf._internal.providers.security.rbac import Permission, Role


@dataclass(frozen=True, slots=True)
class Claims:
    """Claims de identidad — el vocabulario común entre JWT, LDAP y Azure AD.

    ``sub`` es el único campo obligatorio (identificador estable del
    sujeto); el resto es opcional porque ningún proveedor de identidad
    garantiza todos los campos (LDAP no tiene ``locale``/``timezone`` por
    defecto, un API Key no tiene ``email``). ``extra`` guarda cualquier
    claim adicional específico de un proveedor concreto, sin forzar un
    cambio de esquema aquí cada vez que aparece uno nuevo.
    """

    sub: str
    name: str | None = None
    email: str | None = None
    tenant: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    groups: frozenset[str] = field(default_factory=frozenset)
    locale: str | None = None
    timezone: str | None = None
    department: str | None = None
    job_title: str | None = None
    extra: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de estos claims."""
        return {
            "sub": self.sub,
            "name": self.name,
            "email": self.email,
            "tenant": self.tenant,
            "roles": sorted(self.roles),
            "permissions": sorted(self.permissions),
            "groups": sorted(self.groups),
            "locale": self.locale,
            "timezone": self.timezone,
            "department": self.department,
            "jobTitle": self.job_title,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True, slots=True)
class Identity:
    """Quién es el llamante, tal como lo estableció un ``IdentityProvider``.

    Anterior a la resolución de autorización (ver ``Principal``) — un
    ``Identity`` describe *quién* es alguien, nunca *qué puede hacer*.
    """

    id: str
    provider_id: str
    claims: Claims
    authenticated: bool = True

    @property
    def name(self) -> str | None:
        """Atajo a ``claims.name``."""
        return self.claims.name


#: Identidad anónima compartida — mismo espíritu que
#: ``providers.security.security_context.ANONYMOUS``, pero a nivel de
#: ``Identity`` en vez de ``SecurityContext``.
ANONYMOUS_IDENTITY = Identity(
    id="anonymous", provider_id="anonymous", claims=Claims(sub="anonymous"), authenticated=False
)


@dataclass(frozen=True, slots=True)
class AuthenticationCredentials:
    """Envoltorio genérico de credenciales que recibe ``IdentityProvider.authenticate``.

    Cada proveedor usa solo los campos que necesita (JWT: ``token``; API
    Key: ``api_key``; LDAP: ``username``/``password``) — el resto queda en
    ``None``. ``scheme`` es lo que un ``IdentityProviderRegistry`` usa para
    enrutar hacia el proveedor correcto sin que cada uno tenga que
    inspeccionar los headers HTTP crudos.
    """

    scheme: str
    token: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """Lo que devuelve un ``IdentityProvider`` tras autenticar con éxito."""

    identity: Identity

    @property
    def provider_id(self) -> str:
        """Atajo a ``identity.provider_id``."""
        return self.identity.provider_id


@dataclass(frozen=True, slots=True)
class Principal:
    """El sujeto de autorización: una ``Identity`` con roles/permisos/tenant ya resueltos.

    ``Identity`` responde "quién eres"; ``Principal`` responde "qué podés
    hacer" — la separación permite que el mismo motor de autorización
    (RBAC + políticas) funcione igual sin importar qué ``IdentityProvider``
    estableció la identidad original.
    """

    identity: Identity
    roles: frozenset[Role] = field(default_factory=frozenset)
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    tenant_id: str | None = None

    @property
    def id(self) -> str:
        """Atajo a ``identity.id``."""
        return self.identity.id

    @property
    def is_authenticated(self) -> bool:
        """Atajo a ``identity.authenticated``."""
        return self.identity.authenticated

    def has_role(self, name: str) -> bool:
        """``True`` si alguno de los roles de este principal se llama ``name``."""
        return any(role.name == name for role in self.roles)

    def has_permission(self, permission: Permission) -> bool:
        """``True`` si ``permission`` está en ``permissions`` o la otorga algún rol."""
        if permission in self.permissions:
            return True
        return any(role.grants(permission) for role in self.roles)


#: Principal anónimo compartido — sin roles, sin permisos, sin tenant.
ANONYMOUS_PRINCIPAL = Principal(identity=ANONYMOUS_IDENTITY)

#: Regla de una ``Policy``: recibe el ``Principal`` en evaluación, devuelve
#: si la política se satisface.
PolicyRule = Callable[[Principal], bool]


@dataclass(frozen=True, slots=True)
class Policy:
    """Una política de autorización con nombre — más expresiva que un permiso plano.

    A diferencia de RBAC (rol → conjunto fijo de permisos), una ``Policy``
    puede depender de cualquier condición sobre el ``Principal`` (tenant,
    combinación de claims, hora del día vía closure, etc.) — ``rule`` es
    simplemente un callable, sin un DSL propio que aprender.
    """

    name: str
    rule: PolicyRule
    description: str = ""

    def evaluate(self, principal: Principal) -> bool:
        """Aplica ``rule`` sobre ``principal``."""
        return self.rule(principal)


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Un access token + refresh token emitidos juntos por un ``TokenProvider``."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 0

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) — forma típica de una respuesta de login."""
        return {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "tokenType": self.token_type,
            "expiresIn": self.expires_in,
        }
