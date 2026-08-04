"""Implementaciones concretas de ``IdentityProvider`` (contracts/security.py).

Cinco proveedores completos (Sprint 2.7, ver ADR-007): ``anonymous.py``,
``api_key.py``, ``jwt.py``, ``ldap.py``, ``azure_ad.py`` (este último
extiende ``oidc.py``, reutilizable para Keycloak/Auth0/Okta/Google sin
rediseño). ``registry.py`` enruta credenciales entrantes hacia el
proveedor correcto — lo usa ``SecurityMiddleware``.
"""

from __future__ import annotations
