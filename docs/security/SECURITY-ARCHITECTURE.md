# Plataforma de Seguridad Empresarial — TEAF

Documentación del Sprint 2.7 (Enterprise Security Platform, v0.7.0-alpha, [ADR-007](../architecture/adr/ADR-007-enterprise-security-stack.md)): autenticación y autorización empresarial completas, diseñadas alrededor de un único contrato — `IdentityProvider` — nunca acopladas a JWT ni a ningún mecanismo concreto. Complementa — no reemplaza — [docs/standards/SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md), que sigue siendo la fuente normativa de prácticas obligatorias; este documento describe cómo TEAF las implementa.

## 1. El contrato central: `IdentityProvider`

```python
class IdentityProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult: ...

    def supports(self, credentials: AuthenticationCredentials) -> bool:
        return credentials.scheme == self.provider_id
```

Cinco implementaciones concretas en este Sprint — **Anonymous**, **JWT**, **API Key**, **LDAP**, **Azure AD** — todas intercambiables entre sí desde el punto de vista de `SecurityMiddleware`/`IdentityProviderRegistry`, que nunca conocen el mecanismo concreto. Añadir un sexto proveedor (Keycloak, Auth0, Okta, Google, GitHub, SAML) nunca requiere tocar el middleware ni el registro — ver sección 5.

## 2. Arquitectura y capas

```
teaf/_internal/contracts/security.py         # IdentityProvider, OAuth2IdentityProvider, SAMLIdentityProvider,
                                              # TokenProvider, SessionProvider, PermissionResolver, RoleResolver,
                                              # PolicyEvaluator, PasswordHasher, CryptoProvider

teaf/_internal/security/
├── models.py                    # Claims, Identity, Principal, Policy, TokenPair — ver CLAIMS.md
├── exceptions.py                  # Jerarquía sobre AuthenticationException/AuthorizationException (401/403 automáticos)
├── context.py                       # build_security_context() — Principal -> SecurityContext
├── middleware.py                      # SecurityMiddleware — resuelve identidad en cada petición
├── decorators.py                        # @authorize()/@allow_anonymous()
├── dependencies.py                        # current_identity/current_principal/current_claims/current_security_context
├── identity_providers/
│   ├── anonymous.py                         # AnonymousIdentityProvider — respaldo, siempre disponible
│   ├── jwt.py                                 # JWTIdentityProvider — adapta JWTTokenProvider
│   ├── api_key.py                               # ApiKeyIdentityProvider — adapta ApiKeyProvider
│   ├── ldap.py                                    # LDAPIdentityProvider — ver LDAP.md
│   ├── oidc.py                                      # OpenIDConnectIdentityProvider — base genérica reutilizable
│   ├── azure_ad.py                                    # AzureADIdentityProvider(OpenIDConnectIdentityProvider) — ver AZURE-AD.md
│   └── registry.py                                      # IdentityProviderRegistry — enrutamiento por scheme
├── tokens/
│   ├── jwt_provider.py            # JWTTokenProvider — ver JWT.md
│   └── api_key_provider.py          # ApiKeyProvider — ver APIKEY.md
├── crypto/
│   ├── password_hasher.py           # Argon2PasswordHasher (por defecto), BcryptPasswordHasher
│   └── crypto_provider.py             # HmacCryptoProvider — firmas, no contraseñas
└── authorization/
    ├── rbac.py                          # StaticRoleResolver, RolePermissionResolver, PrincipalResolver — ver RBAC.md
    └── policy_evaluator.py                 # DefaultPolicyEvaluator

teaf/_internal/providers/security/security_context.py   # SecurityContext (Sprint 2.2, extendido aditivamente)

teaf/_internal/modules/security/            # El módulo SDK que empaqueta todo lo anterior
├── configuration.py                # SecurityConfiguration (dataclass + from_mapping)
├── health.py                         # SecurityHealth
├── manifest.py                         # build_security_manifest()
└── module.py                             # SecurityModule(ModuleBase)

teaf/security.py                    # La fachada pública — ver sección 4
```

**Dirección de dependencias**: `teaf/_internal/modules/security/` importa de `teaf/_internal/security/`, nunca al revés — igual patrón que `modules/database/` → `providers/database/` (ver [DATABASE.md](../modules/database/DATABASE.md)). `teaf/_internal/security/models.py` reutiliza `Role`/`Permission` de `teaf/_internal/providers/security/rbac.py` (Sprint 2.2) en vez de duplicarlos.

## 3. Cómo se resuelve la identidad de cada petición

```
Petición HTTP
  │
  ▼
SecurityMiddleware.dispatch()
  │  1. Extrae credenciales (Authorization: Bearer/Basic, X-API-Key, ?api_key=)
  │  2. "Sniffing" del scheme: un Bearer se enruta a "jwt" o "azure-ad" según el
  │     claim `iss` (sin verificar la firma todavía — solo para enrutar)
  │  3. IdentityProviderRegistry.resolve(credentials) -> IdentityProvider | None
  │  4. provider.authenticate(credentials) -> Identity (o AuthenticationException)
  │  5. PrincipalResolver.resolve(identity) -> Principal (roles + permisos efectivos)
  │  6. build_security_context(principal) -> SecurityContext, publicado en un ContextVar
  ▼
Endpoint (lee el SecurityContext vía current_principal/current_identity/current_claims,
          o exige autorización vía @authorize()/@allow_anonymous())
```

`SecurityMiddleware` **nunca bloquea una petición por falta de autenticación** — toda petición resuelve, como mínimo, un `Principal` anónimo. La imposición de la política es responsabilidad de `@authorize()`/`@allow_anonymous()`, aplicados por endpoint (ver [RBAC.md](RBAC.md)).

## 4. Cómo se cablea (`teaf.security`, la API pública)

`SecurityModule` **no se expone** desde `teaf.security` — mismo criterio que `DatabaseModule` (ver [PUBLIC-API.md](../public-api/PUBLIC-API.md), sección 6): ningún módulo real del framework se expone desde `teaf/`. Una aplicación construye la plataforma de seguridad componiendo directamente las piezas públicas:

```python
from teaf import Application
from teaf.security import (
    AnonymousIdentityProvider, JWTIdentityProvider, JWTProvider,
    IdentityProviderRegistry, PrincipalResolver, StaticRoleResolver,
    SecurityMiddleware, authorize, current_principal,
)

jwt_provider = JWTProvider(secret="...")
provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
)
principal_resolver = PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={...}))

app = Application()
app.asgi.add_middleware(
    SecurityMiddleware, provider_registry=provider_registry, principal_resolver=principal_resolver
)
```

Ver [`examples/jwt-login/`](../../examples/jwt-login/), [`examples/role-based-endpoint/`](../../examples/role-based-endpoint/), y el resto de los 8 ejemplos de seguridad listados en [`examples/README.md`](../../examples/README.md).

Internamente (dentro de este repositorio, no para consumidores externos), `SecurityModule` (`teaf/_internal/modules/security/module.py`) empaqueta exactamente lo mismo como un `ModuleBase` — construye todos sus proveedores en `__init__`, expone `provider_registry`/`principal_resolver` como atributos públicos *antes* de que `Application(modules=[...])` arranque el ciclo de vida ASGI, precisamente para que puedan leerse y usarse al configurar `SecurityMiddleware` (que debe añadirse antes de que arranque ese ciclo). Ver `tests/integration/test_security_module_bootstrap.py` para la prueba de este patrón de extremo a extremo.

## 5. Extensibilidad: cómo se añade un proveedor sin rediseño

`OpenIDConnectIdentityProvider` (expuesto como `OpenIDConnectProvider`) implementa descubrimiento OIDC (`.well-known/openid-configuration`), validación JWKS y el Authorization Code Flow — todo lo que un proveedor OIDC concreto necesita. `AzureADIdentityProvider` es su primera especialización: solo fija `discovery_url` y sobrescribe `_map_claims()`/`_issuer_for_validation()`. **Keycloak, Auth0, Okta y Google** se añadirían de la misma forma — una subclase de `OpenIDConnectProvider`, sin tocar `SecurityMiddleware`, `IdentityProviderRegistry` ni ningún otro proveedor existente.

**GitHub/Apple** (OAuth2 no-OIDC) y **SAML** tienen contratos preparados y deliberadamente sin implementación (`OAuth2IdentityProvider`, `SAMLIdentityProvider`, ambos expuestos en `teaf.security`) — forzarlos a la forma OIDC introduciría una abstracción incorrecta (SAML es XML/assertions, no JWT/JWKS).

## 6. Eventos publicados

`SecurityMiddleware` (autenticación) y `JWTTokenProvider`/`ApiKeyProvider` (tokens) publican vía `EventBus` cuando se les inyecta uno:

| Evento | Cuándo |
|---|---|
| `authentication.started` | Al iniciar la resolución de credenciales de una petición. |
| `authentication.succeeded` | Un `IdentityProvider` autenticó con éxito. |
| `authentication.failed` | Ningún proveedor pudo autenticar las credenciales presentadas. |
| `authorization.started`/`succeeded`/`failed` | Reservados para un futuro `AuthorizationProvider` real con eventos (los contratos de Sprint 2.1 siguen siendo mínimos). |
| `token.created`/`refreshed`/`revoked` | Declarados en el manifiesto del módulo (`security.tokens`) para que una aplicación los use si conecta su propio `EventBus`. |
| `apikey.validated` | Declarado en el manifiesto (`security.tokens`). |
| `ldap.login` / `azuread.login` | Declarados en el manifiesto para observabilidad específica de esos proveedores. |

## 7. Documentos relacionados

| Documento | Contenido |
|---|---|
| [CLAIMS.md](CLAIMS.md) | `Claims`/`Identity`/`Principal`/`SecurityContext` — el modelo de dominio completo. |
| [RBAC.md](RBAC.md) | Roles, permisos, políticas, y los decoradores `@authorize()`/`@allow_anonymous()`. |
| [JWT.md](JWT.md) | `JWTProvider` — emisión, verificación, refresco, revocación, rotación. |
| [APIKEY.md](APIKEY.md) | `ApiKeyProvider` — transporte, scopes, expiración, revocación, rotación. |
| [LDAP.md](LDAP.md) | `LDAPProvider` — bind, búsqueda de grupos, mapeo a roles/permisos. |
| [AZURE-AD.md](AZURE-AD.md) | `AzureADProvider` — OIDC, JWKS, multi-tenant. |
| [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md) | Prácticas normativas obligatorias que esta plataforma implementa. |
| [ADR-007](../architecture/adr/ADR-007-enterprise-security-stack.md) | Por qué PyJWT/Argon2/BCrypt/ldap3/httpx, y por qué `IdentityProvider` es el contrato central. |
