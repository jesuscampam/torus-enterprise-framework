# JWT — TEAF

`JWTProvider` (alias público de `JWTTokenProvider`) — emisión, verificación, refresco y revocación de JWT vía PyJWT. Ver [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) para la nomenclatura `JWTProvider` vs. `JWTIdentityProvider`.

## 1. Emitir y verificar

```python
from teaf.security import JWTProvider, Identity, Claims

jwt_provider = JWTProvider(
    secret="...",                     # HS256: secreto simétrico. RS256/ES256: clave privada/pública PEM.
    algorithm="HS256",                # cualquiera soportado por PyJWT
    issuer="teaf",
    audience="teaf",
    access_token_ttl_seconds=900,       # 15 minutos (recomendación de SECURITY-STANDARD.md)
    refresh_token_ttl_seconds=1_209_600,  # 14 días
    clock_skew_seconds=30,                  # tolerancia de reloj al validar exp/nbf
)

identity = Identity(id="alice", provider_id="jwt", claims=Claims(sub="alice", roles=frozenset({"admin"})))
token_pair = await jwt_provider.issue(identity)   # TokenPair(access_token, refresh_token, token_type, expires_in)

identity = await jwt_provider.verify(token_pair.access_token)   # Identity, o lanza TokenException/TokenExpiredException
```

Los claims de `Identity.claims` (roles, permisos, groups, tenant, name, email, locale, timezone, department, job_title) se codifican íntegros en el payload del JWT — `verify()` los reconstruye sin ninguna llamada adicional (sin round-trip a una base de datos).

## 2. Refresco con rotación

```python
new_pair = await jwt_provider.refresh(token_pair.refresh_token)
```

**Rotación con revocación-en-reutilización**: cada `refresh()` revoca el refresh token usado antes de emitir el par nuevo. Si alguien reutiliza un refresh token ya canjeado (p. ej. uno robado), `refresh()` falla con `TokenRevokedException` — la cadena de sesión completa debe considerarse comprometida (ver [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md), sección 1).

## 3. Revocación explícita

```python
await jwt_provider.revoke(token_pair.access_token)   # deja de ser válido de inmediato, aunque no haya expirado
```

Revocar un token ya expirado no lanza — por simetría, y para no dejar huecos si el llamador no sabe si aún es válido.

## 4. Dónde vive la lista de revocación

```python
from teaf.security import TokenRevocationStore, InMemoryTokenRevocationStore

class RedisTokenRevocationStore(TokenRevocationStore):
    def is_revoked(self, jti: str) -> bool: ...
    def revoke(self, jti: str, *, expires_at: float) -> None: ...
```

`InMemoryTokenRevocationStore` (el valor por defecto) es suficiente para una sola instancia de proceso. Una aplicación con múltiples instancias debe sustituirla por una implementación respaldada en Redis/base de datos compartida — mismo contrato, sin cambiar `JWTProvider` (Cloud Ready, ver [ADR-005](../architecture/adr/ADR-005-cloud-ready.md)):

```python
jwt_provider = JWTProvider(secret="...", revocation_store=RedisTokenRevocationStore(...))
```

## 5. Autenticar peticiones HTTP: `JWTIdentityProvider`

`JWTProvider` (el emisor/verificador) es distinto de `JWTIdentityProvider` (el adaptador que resuelve identidad en cada petición, consumido por `IdentityProviderRegistry`/`SecurityMiddleware`) — la misma separación que existe entre `ApiKeyProvider` y `ApiKeyIdentityProvider` (ver [APIKEY.md](APIKEY.md)):

```python
from teaf.security import JWTIdentityProvider, IdentityProviderRegistry, AnonymousIdentityProvider

provider_registry = IdentityProviderRegistry(
    [AnonymousIdentityProvider(), JWTIdentityProvider(token_provider=jwt_provider)]
)
```

`SecurityMiddleware` enruta automáticamente `Authorization: Bearer <token>` hacia el proveedor `"jwt"` (o `"azure-ad"`, según el `iss` sin verificar del token — ver [AZURE-AD.md](AZURE-AD.md)).

## 6. Ejemplo completo

Ver [`examples/jwt-login/`](../../examples/jwt-login/): login con usuario/contraseña (`PasswordHasher`) que emite un `TokenPair`, y un endpoint protegido con `@authorize()`.

## 7. Documentos relacionados

| Documento | Contenido |
|---|---|
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Flujo completo de una petición, incluyendo el "sniffing" JWT vs. Azure AD. |
| [CLAIMS.md](CLAIMS.md) | `Identity`/`Claims`/`TokenPair` completos. |
| [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md) | Requisitos normativos de TTL, algoritmos y revocación. |
