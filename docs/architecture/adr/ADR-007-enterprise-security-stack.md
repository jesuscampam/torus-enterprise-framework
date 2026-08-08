# ADR-007: Enterprise Security Stack — Identity Providers, JWT, LDAP, Azure AD, Argon2

## Estado

Aceptado

## Contexto

TEAF llega al Sprint 2.7 con seguridad únicamente como contratos abstractos (`AuthenticationProvider`/`AuthorizationProvider` en `teaf/_internal/contracts/security.py`, `SecurityContext`/`Role`/`Permission` en `teaf/_internal/providers/security/`, Sprint 2.2) — sin una sola implementación concreta. `docs/roadmap/BACKLOG.md` (Épica 2) y `docs/standards/SECURITY-STANDARD.md` solo anticipaban JWT + RBAC + hashing de contraseñas. Las aplicaciones empresariales reales de TORUS (Portal TORUS, Portal NOC, Portal SRE, integraciones SAP/Salesforce) necesitan, además, autenticarse contra Active Directory corporativo (LDAP) y contra Microsoft Entra ID (Azure AD) — mecanismos fuera del alcance original del backlog. Ninguno de los dos requiere solo "añadir una librería": exige decidir la forma misma de la plataforma de seguridad, porque diseñarla alrededor de JWT en exclusiva obligaría a un rediseño estructural en cuanto apareciera el segundo mecanismo de identidad.

## Problema

¿Cómo construye TEAF una plataforma de seguridad que soporte, desde el primer día, múltiples mecanismos de identidad (Anonymous, API Key, JWT, LDAP, Azure AD, y en el futuro OAuth2/OIDC genérico, Keycloak, Auth0, Okta, Google, GitHub, SAML) sin que cada mecanismo nuevo exija tocar el Runtime, el `ServiceContainer` o el middleware existente — y qué librerías de terceros necesita para implementarlo, dado que ninguna existe hoy en el stack?

## Decisión

Se diseña la plataforma alrededor de un contrato `IdentityProvider` (no alrededor de JWT): cada mecanismo de identidad implementa `async def authenticate(credentials: AuthenticationCredentials) -> AuthenticationResult`, se registra contra el `SecurityMiddleware` a través de un `IdentityProviderRegistry`, y produce un `SecurityContext` uniforme independientemente del mecanismo que lo generó. `AuthenticationProvider`/`AuthorizationProvider` (Sprint 2.2) permanecen sin modificar — `IdentityProvider` es un contrato nuevo y paralelo, no un reemplazo, para no romper compatibilidad con lo ya aceptado.

Se implementan completamente cinco proveedores (Anonymous, API Key, JWT, LDAP, Azure AD) y se prepara la arquitectura para el resto mediante una clase base reutilizable `OpenIDConnectIdentityProvider` (descubrimiento OIDC + validación JWKS + mapeo de claims genérico) de la que `AzureADIdentityProvider` es la primera especialización concreta — Keycloak/Auth0/Okta/Google solo necesitarán sobrescribir las URLs de descubrimiento y el mapeo de claims específico de cada proveedor, sin tocar la lógica de validación de tokens. GitHub/Apple (OAuth2 no-OIDC) y SAML quedan como contratos (`OAuth2IdentityProvider`, `SAMLIdentityProvider`) sin implementación, porque su protocolo de negociación es genuinamente distinto (SAML es XML/assertions, no JWT/JWKS) y forzarlos a la forma OIDC introduciría una abstracción incorrecta.

Se adoptan las siguientes librerías nuevas, todas fijadas a versión exacta en `pyproject.toml`/`requirements.txt`:

- **PyJWT `[crypto]` 2.10.1** — firma/verificación JWT (HS256 y RS256/ES256, este último necesario para validar tokens de Azure AD).
- **`ldap3` 2.9.1** — cliente LDAP puro Python (sin enlazar contra `libldap` del sistema, a diferencia de `python-ldap` — preserva Docker First/Cloud Ready).
- **`httpx` 0.28.1** — promovida de dependencia de desarrollo a dependencia de runtime; descubrimiento OIDC, JWKS y Authorization Code Flow de Azure AD, todo async-nativo.
- **`argon2-cffi` 23.1.0** — hashing de contraseñas Argon2id (recomendación OWASP vigente), proveedor por defecto de `PasswordHasher`.
- **`bcrypt` 4.2.1** — proveedor alternativo de `PasswordHasher`, para compatibilidad con hashes preexistentes de aplicaciones migradas a TEAF; el contrato `PasswordHasher` no distingue cuál está activo.

Ver justificación individual de cada librería en [STACK.md](../STACK.md).

## Consecuencias

### Positivas

- Ningún mecanismo de identidad futuro (OAuth2 genérico, Keycloak, Auth0, Okta, Google, GitHub, SAML) exige cambios en el Runtime, el `ServiceContainer`, el `SecurityMiddleware` ni la superficie pública `teaf.*` — solo una nueva clase que implemente `IdentityProvider` (o extienda `OpenIDConnectIdentityProvider`).
- `AuthenticationProvider`/`AuthorizationProvider` y `SecurityContext`/`Role`/`Permission` (Sprint 2.2) permanecen intactos — cero cambios incompatibles para quien ya los usaba.
- `OpenIDConnectIdentityProvider` como clase base reutilizable convierte la promesa "preparado para Keycloak/Auth0/Okta/Google sin rediseño" en código demostrado (Azure AD es la prueba viva de esa reutilización), no solo en una afirmación de diseño.
- `ldap3` y `httpx` mantienen la imagen de contenedor libre de dependencias nativas del sistema operativo, consistente con ADR-005 (Cloud Ready).

### Negativas / Trade-offs

- Cinco librerías nuevas de terceros amplían la superficie de dependencias del framework — cada una fijada a versión exacta y sujeta al mismo proceso de actualización que el resto del stack (Dependabot, ver `.github/dependabot.yml`).
- `ldap3` es síncrono: las llamadas de bind/búsqueda se ejecutan en threadpool (`anyio.to_thread.run_sync`) para no bloquear el event loop — una capa de indirección adicional frente a un cliente async-nativo, que hoy no existe maduro en el ecosistema Python para LDAP.
- El contrato `IdentityProvider` añade una capa de indirección (`AuthenticationCredentials` → `AuthenticationResult` → `SecurityContext`) frente a decodificar un JWT directamente en el middleware — el coste consciente de no acoplar la plataforma a un único mecanismo.
- Los contratos `OAuth2IdentityProvider`/`SAMLIdentityProvider` no tienen implementación concreta en este Sprint — quedan como superficie preparada, no como funcionalidad entregada; una aplicación que los necesite hoy debe implementarlos.
