# security/

Autenticación, autorización y criptografía del framework, en cumplimiento de [SECURITY-STANDARD.md](../../../docs/standards/SECURITY-STANDARD.md). Implementación completa desde Sprint 2.7 — ver [docs/security/SECURITY-ARCHITECTURE.md](../../../docs/security/SECURITY-ARCHITECTURE.md) para el detalle completo; expuesto públicamente vía `teaf.security` (`teaf/security.py`), nunca importado directamente por un consumidor externo.

## Responsabilidad

- El contrato `IdentityProvider` (`teaf._internal.contracts.security`) y sus cinco implementaciones: Anonymous, JWT, API Key, LDAP, Azure AD (`identity_providers/`).
- Emisión, verificación, refresco y revocación de tokens **JWT** y **API Keys** (`tokens/`).
- Modelo de autorización **RBAC** + políticas arbitrarias (`authorization/`) — roles, permisos, `Policy`.
- Hashing de contraseñas (Argon2id/BCrypt, `crypto/password_hasher.py`) y firmas HMAC (`crypto/crypto_provider.py`).
- `SecurityMiddleware` (resuelve identidad en cada petición) y los decoradores `@authorize()`/`@allow_anonymous()` (`decorators.py`).
- El modelo de dominio compartido: `Claims`/`Identity`/`Principal`/`Policy` (`models.py`).

## Qué NO debe contener

- Lógica de negocio no relacionada con seguridad.
- Reglas de autorización de un dominio específico hardcodeadas de forma ad-hoc fuera del modelo RBAC/políticas centralizado.

## Principio rector

Toda decisión de "quién eres" e "qué podés hacer" pasa por esta capa, siempre a través del contrato `IdentityProvider` — ninguna otra capa implementa su propia lógica de autenticación/autorización paralela.
