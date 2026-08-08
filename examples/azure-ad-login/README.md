# azure-ad-login/

Validar tokens de Microsoft Entra ID (Azure AD) con `AzureADProvider`: descubrimiento OIDC, JWKS y mapeo de claims propios de Azure AD (`oid`, `tid`, `preferred_username`).

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- El ejemplo mockea el tenant de Azure AD (`httpx.MockTransport`) para poder ejecutarse sin credenciales ni red real — en producción se construye `AzureADProvider(tenant=..., client_id=..., client_secret=...)` sin `http_client` y habla con `login.microsoftonline.com` de verdad.
- `get_authorization_url()` es el primer paso real de un login con Azure AD (redirigir al usuario a Microsoft) — el ejemplo lo imprime aunque no lo sigue (no hay navegador en este script).
- `AzureADProvider` es una especialización de `OpenIDConnectProvider`, la base genérica reutilizable para Keycloak/Auth0/Okta/Google (ver ADR-007) — este ejemplo es, en la práctica, una demostración de esa base también.
- La validación de firma es real: el JWT se firma con una clave RSA generada en el propio script y se verifica contra el JWKS "publicado" por el mock — no es un atajo que salte la criptografía.
