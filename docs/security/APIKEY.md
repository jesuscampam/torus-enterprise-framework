# API Key — TEAF

`ApiKeyProvider` — emisión, verificación, revocación, scopes y rotación de API Keys. Transporte-agnóstico; `ApiKeyIdentityProvider` es quien lo conecta con HTTP.

## 1. Emitir, verificar, revocar, rotar

```python
from teaf.security import ApiKeyProvider

api_key_provider = ApiKeyProvider(secret="...")   # pepper del servidor, nunca viaja con la key

raw_key, record = api_key_provider.issue(
    principal_id="ci-pipeline",
    scopes=frozenset({"reports:read"}),
    ttl=None,   # o un timedelta — None significa que no expira
)
# raw_key: "teaf_..." — la única vez que existe en texto plano; mostrarla una vez y descartarla.
# record: ApiKeyRecord — nunca contiene raw_key, solo su hash.

record = api_key_provider.verify(raw_key, required_scope="reports:read")   # o lanza ApiKeyException

api_key_provider.revoke(record.id)          # deja de ser válida de inmediato

new_raw_key = api_key_provider.rotate(record.id)   # revoca la anterior, emite una nueva con el mismo principal/scopes
```

La clave se hashea con **HMAC-SHA256** (no Argon2/BCrypt): una API Key ya es de alta entropía aleatoria (`secrets.token_urlsafe(32)`), a diferencia de una contraseña humana de baja entropía que sí necesita un hash lento — ver la justificación completa en el docstring de `teaf._internal.security.tokens.api_key_provider`.

## 2. Dónde vive el almacén

```python
from teaf.security import ApiKeyStore, InMemoryApiKeyStore

class DatabaseApiKeyStore(ApiKeyStore):
    def save(self, record: ApiKeyRecord) -> None: ...
    def get(self, key_id: str) -> ApiKeyRecord | None: ...
    def find_by_hash(self, hashed_key: str) -> ApiKeyRecord | None: ...
    def list_for_principal(self, principal_id: str) -> tuple[ApiKeyRecord, ...]: ...
```

`InMemoryApiKeyStore` (el valor por defecto) es suficiente para una sola instancia o pruebas. Una aplicación real sustituye el almacén por una implementación respaldada en base de datos sin cambiar `ApiKeyProvider`:

```python
api_key_provider = ApiKeyProvider(secret="...", store=DatabaseApiKeyStore(...))
```

## 3. Transporte: header, header propio, o query string

`ApiKeyIdentityProvider` (el adaptador que `IdentityProviderRegistry`/`SecurityMiddleware` consume) autentica peticiones que traen la key por `X-API-Key` (por defecto) o `?api_key=...` — ambos configurables en `SecurityMiddleware(api_key_header=..., api_key_query_param=...)`:

```python
from teaf.security import ApiKeyIdentityProvider, IdentityProviderRegistry, AnonymousIdentityProvider

provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), ApiKeyIdentityProvider(api_key_provider=api_key_provider)]
)
```

## 4. Scopes como permisos

`ApiKeyIdentityProvider` traduce los *scopes* de la key directamente a `Claims.permissions` — una API Key no tiene nombre/email/roles como una identidad humana, así que `Identity.claims` solo rellena `sub` (el `principal_id`) y `permissions`. Esto significa que `@authorize(permission=...)` (ver [RBAC.md](RBAC.md)) funciona sobre una API Key sin ningún catálogo de roles:

```python
@app.get("/reports")
@authorize(permission="reports:read")
def reports(): ...
```

## 5. Ejemplo completo

Ver [`examples/api-key-auth/`](../../examples/api-key-auth/): emisión, uso vía header/query string, revocación y rotación de extremo a extremo.

## 6. Documentos relacionados

| Documento | Contenido |
|---|---|
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Flujo completo de una petición. |
| [RBAC.md](RBAC.md) | `@authorize(permission=...)` sobre los scopes de una API Key. |
| [JWT.md](JWT.md) | El mismo patrón "emisor" vs. "adaptador de identidad" (`JWTProvider`/`JWTIdentityProvider`). |
