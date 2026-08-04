# Claims, Identity, Principal, SecurityContext — TEAF

El modelo de dominio de la plataforma de seguridad (Sprint 2.7). Cuatro tipos, cada uno respondiendo una pregunta distinta — ver [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) para dónde encajan en el flujo de una petición.

## 1. `Claims` — el vocabulario común

```python
@dataclass(frozen=True, slots=True)
class Claims:
    sub: str                                    # único campo obligatorio
    name: str | None = None
    email: str | None = None
    tenant: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    groups: frozenset[str] = frozenset()
    locale: str | None = None
    timezone: str | None = None
    department: str | None = None
    job_title: str | None = None
    extra: Mapping[str, object] = {}            # cualquier claim propio de un proveedor concreto
```

`sub` es el único campo garantizado por todo `IdentityProvider` — el resto es opcional porque ningún proveedor los rellena todos (LDAP no tiene `locale`/`timezone` por defecto; una API Key no tiene `email`). `extra` evita que aparecer un claim nuevo de un proveedor concreto obligue a cambiar este esquema compartido.

## 2. `Identity` — quién es el llamante

```python
@dataclass(frozen=True, slots=True)
class Identity:
    id: str
    provider_id: str        # "jwt", "ldap", "azure-ad", "api-key", "anonymous"
    claims: Claims
    authenticated: bool = True
```

Lo que un `IdentityProvider.authenticate()` produce — anterior a la resolución de autorización. `ANONYMOUS_IDENTITY` (compartida, `authenticated=False`) es lo que usa `AnonymousIdentityProvider`.

## 3. `Principal` — qué puede hacer

```python
@dataclass(frozen=True, slots=True)
class Principal:
    identity: Identity
    roles: frozenset[Role] = frozenset()
    permissions: frozenset[Permission] = frozenset()   # efectivos: directos + los que otorgan los roles
    tenant_id: str | None = None

    @property
    def is_authenticated(self) -> bool: ...   # atajo a identity.authenticated
    def has_role(self, name: str) -> bool: ...
    def has_permission(self, permission: Permission) -> bool: ...
```

Lo produce `PrincipalResolver.resolve(identity)` (ver [RBAC.md](RBAC.md)) combinando `RoleResolver` + `PermissionResolver`. `ANONYMOUS_PRINCIPAL` (sin roles, sin permisos, sin tenant) es el valor por defecto cuando no hay autenticación.

## 4. `SecurityContext` — publicado por petición

`teaf._internal.providers.security.security_context.SecurityContext` (Sprint 2.2, extendido aditivamente en Sprint 2.7) es lo que `SecurityMiddleware` publica en un `ContextVar` para cada petición — el mismo patrón que `core/context.py` usa para el correlation-id, así que no hace falta resetearlo manualmente (cada petición ASGI corre en su propia `asyncio.Task`).

```python
@dataclass(frozen=True, slots=True)
class SecurityContext:
    principal_id: str | None = None
    roles: frozenset[Role] = frozenset()
    permissions: frozenset[Permission] = frozenset()
    identity: Identity | None = None
    principal: Principal | None = None
    tenant_id: str | None = None
    provider_id: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None

    @property
    def is_authenticated(self) -> bool: ...
    def has_permission(self, permission: Permission) -> bool: ...
```

Un endpoint casi nunca lo lee directamente — usa las dependencias de FastAPI públicas:

```python
from fastapi import Depends
from teaf.security import current_identity, current_principal, current_claims, current_security_context

@app.get("/me")
def me(principal: Principal = Depends(current_principal)):
    return {"id": principal.id, "roles": [r.name for r in principal.roles]}
```

Las cuatro (`current_identity`/`current_principal`/`current_claims`/`current_security_context`) son dependencias válidas de cero parámetros — leen el `ContextVar` que el middleware ya publicó, nunca inyectan el `Request` en sí. Todas devuelven el valor anónimo correspondiente si no hay autenticación — nunca `None` ni una excepción.

## 5. `AuthenticationCredentials`/`AuthenticationResult`

El envoltorio genérico que un `IdentityProvider.authenticate()` recibe y produce:

```python
@dataclass(frozen=True, slots=True)
class AuthenticationCredentials:
    scheme: str                    # "jwt", "api-key", "ldap", "azure-ad", "anonymous"
    token: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    extra: Mapping[str, object] = {}

@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    identity: Identity
```

Cada proveedor usa solo los campos que necesita — el resto queda en `None`. `scheme` es lo que `IdentityProviderRegistry` usa para enrutar sin que cada proveedor tenga que inspeccionar headers HTTP crudos.

## 6. Documentos relacionados

| Documento | Contenido |
|---|---|
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Visión general de la plataforma y el flujo completo de una petición. |
| [RBAC.md](RBAC.md) | Cómo se resuelven `roles`/`permissions` — `RoleResolver`, `PermissionResolver`, `PrincipalResolver`. |
