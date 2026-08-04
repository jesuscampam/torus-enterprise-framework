# examples/

Ejemplos mínimos de la API pública de TEAF (`teaf/`, ver [docs/public-api/](../docs/public-api/)). Cada uno importa **exclusivamente** `from teaf import ...` — ninguno conoce `teaf/_internal/` (ver [IMPORT-GUIDE.md](../docs/public-api/IMPORT-GUIDE.md)). Verificado automáticamente por `scripts/check_public_api_boundary.py` y por `tests/unit/test_import_boundary_checker.py`.

## Requisito previo

```bash
pip install -e .
```

## Ejemplos

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`hello-world/`](hello-world/) | Lo mínimo: construir una `Application`, arrancar y apagar su `Runtime`. | `python examples/hello-world/main.py` |
| [`basic-module/`](basic-module/) | Construir un módulo propio con `Module`/`ModuleBuilder` y registrarlo contra un `Runtime`. | `python examples/basic-module/main.py` |
| [`application-bootstrap/`](application-bootstrap/) | Una `Application` completa con un módulo propio ya registrado, más introspección del `Runtime`. | `python examples/application-bootstrap/main.py` |
| [`module-registration/`](module-registration/) | Registrar un módulo con la Module Registration API (`Application(modules=[...])`) — sin `bootstrap()` manual, sin `asyncio.run()`, sin threads. | `python examples/module-registration/main.py` |

Progresión sugerida: léelos en ese orden — cada uno añade una pieza sobre el anterior.

## Plataforma de seguridad (Sprint 2.7, ADR-007)

Cada uno construye su propio `IdentityProviderRegistry`/`PrincipalResolver` y los conecta con `SecurityMiddleware` (`app.asgi.add_middleware(...)`) — el mismo patrón de cableado manual documentado en [`teaf/security.py`](../teaf/security.py) (`SecurityModule` no se expone públicamente, igual que `DatabaseModule`, ver [PUBLIC-API.md](../docs/public-api/PUBLIC-API.md)).

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`jwt-login/`](jwt-login/) | Login con usuario/contraseña (`PasswordHasher`) que emite un JWT (`JWTProvider`), y un endpoint protegido con `@authorize()`. | `python examples/jwt-login/main.py` |
| [`api-key-auth/`](api-key-auth/) | Emitir/usar/rotar/revocar una API Key (`ApiKeyProvider`) y un endpoint protegido por *scope*. | `python examples/api-key-auth/main.py` |
| [`ldap-login/`](ldap-login/) | Bind contra LDAP/Active Directory (`LDAPProvider`) y conversión de grupos a roles. | `python examples/ldap-login/main.py` |
| [`azure-ad-login/`](azure-ad-login/) | Validar tokens de Microsoft Entra ID (`AzureADProvider`): descubrimiento OIDC + JWKS. | `python examples/azure-ad-login/main.py` |
| [`role-based-endpoint/`](role-based-endpoint/) | Proteger un endpoint con `@authorize(role="admin")` (RBAC). | `python examples/role-based-endpoint/main.py` |
| [`permission-based-endpoint/`](permission-based-endpoint/) | Proteger un endpoint con `@authorize(permission=...)`, desacoplado del nombre del rol. | `python examples/permission-based-endpoint/main.py` |
| [`policy-based-endpoint/`](policy-based-endpoint/) | Proteger un endpoint con `@authorize(policy=...)` — una regla arbitraria sobre el `Principal`. | `python examples/policy-based-endpoint/main.py` |
| [`anonymous-endpoint/`](anonymous-endpoint/) | Marcar un endpoint como público a propósito con `@allow_anonymous()`, en contraste con uno protegido. | `python examples/anonymous-endpoint/main.py` |
