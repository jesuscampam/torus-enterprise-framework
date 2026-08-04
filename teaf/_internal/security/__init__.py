"""Plataforma de seguridad empresarial de TEAF (Sprint 2.7, ver ADR-007).

Diseñada alrededor de un contrato `IdentityProvider` — no alrededor de JWT
en exclusiva —, de forma que Anonymous, API Key, JWT, LDAP y Azure AD (y en
el futuro OAuth2 genérico, Keycloak, Auth0, Okta, Google, GitHub, SAML)
conviven como implementaciones intercambiables sin tocar el Runtime, el
`ServiceContainer` ni el `SecurityMiddleware`.

Reutiliza (no reemplaza) `teaf/_internal/providers/security/` (Sprint 2.2:
`SecurityContext`, `Role`, `Permission`, `AuthenticationProvider`,
`AuthorizationProvider`) — este paquete es la capa que faltaba por encima:
proveedores de identidad concretos, tokens, criptografía y el motor de
autorización (RBAC + políticas).
"""

from __future__ import annotations
