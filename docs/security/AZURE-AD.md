# Azure AD (Microsoft Entra ID) — TEAF

`AzureADProvider` — validación de tokens de Microsoft Entra ID vía OIDC/JWKS, y la base genérica (`OpenIDConnectProvider`) sobre la que se construye. Ver [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md), sección 5, para cómo esta base habilita Keycloak/Auth0/Okta/Google sin rediseño.

## 1. `OpenIDConnectProvider` — la base genérica

Implementa, sin acoplarse a ningún proveedor concreto:

- **Descubrimiento OIDC** (`.well-known/openid-configuration`), cacheado tras la primera llamada.
- **Validación de tokens vía JWKS** — implementación propia (no `jwt.PyJWKClient`, que hace sus propias peticiones HTTP con `urllib` ignorando cualquier `httpx.AsyncClient` inyectado, rompiendo tanto el modelo async del framework como la inyección para pruebas — ver el docstring de `oidc.py`). Refresca el JWKS una vez si un `kid` no se encuentra (resiliencia ante rotación de claves del emisor).
- **Authorization Code Flow**: `get_authorization_url()` + `exchange_code_for_token()`.

Un proveedor concreto solo necesita fijar `discovery_url` y, si sus claims no son estándar, sobrescribir `_map_claims()` (y, si es multi-tenant, `_issuer_for_validation()`).

## 2. `AzureADProvider`

```python
from teaf.security import AzureADProvider

azure_ad_provider = AzureADProvider(
    tenant="11111111-1111-1111-1111-111111111111",   # un tenant concreto, o "common"/"organizations"/"consumers"
    client_id="...",
    client_secret=None,                                 # opcional — necesario para exchange_code_for_token en confidential clients
    allowed_tenants=None,                                  # solo relevante en modo multi-tenant, ver sección 3
)
```

Mapea claims propios de Azure AD: `oid` (más estable que `sub` como identificador), `tid` (tenant), `preferred_username` (usado como email), `roles`/`groups` (App Roles/grupos, si la aplicación de Azure AD está configurada para emitirlos).

## 3. Multi-tenant

Cuando `tenant` es `"common"`/`"organizations"`/`"consumers"`, el documento de descubrimiento de Microsoft trae un `issuer` con el placeholder literal `{tenantid}` sin resolver — `AzureADProvider` omite la validación estricta de `iss` en ese caso y valida el tenant real del token sobre el claim `tid`, contra `allowed_tenants`:

```python
azure_ad_provider = AzureADProvider(
    tenant="common", client_id="...", allowed_tenants=frozenset({"tenant-a-id", "tenant-b-id"})
)
```

Sin `allowed_tenants`, cualquier tenant de Azure AD podría autenticarse contra la aplicación — establecerlo es obligatorio en producción para un cliente multi-tenant.

## 4. Conectarlo

```python
from teaf.security import IdentityProviderRegistry, AnonymousIdentityProvider

provider_registry = IdentityProviderRegistry([AnonymousIdentityProvider(), azure_ad_provider])
```

`SecurityMiddleware` enruta `Authorization: Bearer <token>` a `"azure-ad"` (en vez de `"jwt"`) leyendo el claim `iss` sin verificar la firma todavía — la verificación criptográfica real ocurre dentro de `AzureADProvider.authenticate()`.

## 5. Liberar el cliente HTTP

`AzureADProvider` (heredado de `OpenIDConnectProvider`) mantiene un `httpx.AsyncClient` propio salvo que se inyecte uno — `await provider.aclose()` lo libera. Si se registra vía `SecurityModule(identity_providers=[azure_ad_provider])` (uso interno del framework, ver [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md)), `dispose()` lo llama automáticamente por duck-typing.

## 6. Probarlo sin un tenant real

Igual que [LDAP.md](LDAP.md), `AzureADProvider(http_client=...)` acepta un `httpx.AsyncClient` con `transport=httpx.MockTransport(...)` — ver [`examples/azure-ad-login/`](../../examples/azure-ad-login/) para un ejemplo completo que firma un JWT con una clave RSA generada en el propio script y lo valida contra un JWKS mockeado, sin atajos: la verificación de firma es real.

## 7. Documentos relacionados

| Documento | Contenido |
|---|---|
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Cómo `OpenIDConnectProvider` habilita futuros proveedores sin rediseño. |
| [ADR-007](../architecture/adr/ADR-007-enterprise-security-stack.md) | Por qué no se usa `jwt.PyJWKClient`, y la elección de `httpx`. |
