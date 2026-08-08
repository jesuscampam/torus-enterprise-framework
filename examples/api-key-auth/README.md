# api-key-auth/

Emitir, usar (vía header o query string), rotar y revocar una API Key con `ApiKeyProvider`, y un endpoint protegido por *scope* (`@authorize(permission=...)`).

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- La clave en texto plano (`raw_key`) solo existe una vez, al emitirla — `ApiKeyProvider` solo guarda su hash (HMAC-SHA256).
- `ApiKeyIdentityProvider` traduce los *scopes* de la key a `Claims.permissions` — de ahí que `@authorize(permission="reports:read")` funcione sin ningún catálogo de roles.
- `SecurityMiddleware` acepta la key tanto por header (`X-API-Key`) como por query string (`?api_key=...`).
- Tras `revoke()`, la misma key deja de autenticar de inmediato; `rotate()` la reemplaza por una nueva conservando el mismo principal/scopes.
