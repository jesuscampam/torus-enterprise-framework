"""Excepciones de la plataforma de seguridad.

Todas heredan de ``AuthenticationException``/``AuthorizationException``
(``teaf/_internal/core/exceptions.py``, Sprint 2.1) — nunca directamente de
``ApplicationException`` — para que ``middleware/exception_handler.py``
las traduzca automáticamente a HTTP 401/403 sin necesitar mapeos nuevos.
"""

from __future__ import annotations

from teaf._internal.core.exceptions import AuthenticationException, AuthorizationException


class IdentityProviderException(AuthenticationException):
    """Ningún ``IdentityProvider`` registrado pudo (o quiso) manejar las credenciales."""

    default_error_code = "identity-provider-error"


class TokenException(AuthenticationException):
    """Un token (JWT o API Key) es inválido, expiró o fue revocado."""

    default_error_code = "token-error"


class TokenExpiredException(TokenException):
    """El token es válido en forma pero su ``exp`` ya pasó."""

    default_error_code = "token-expired"


class TokenRevokedException(TokenException):
    """El token fue revocado explícitamente antes de expirar."""

    default_error_code = "token-revoked"


class ApiKeyException(AuthenticationException):
    """La API Key es inválida, expiró, fue revocada o no tiene un scope requerido."""

    default_error_code = "api-key-error"


class LdapException(AuthenticationException):
    """Falló el bind o la búsqueda de grupos contra el servidor LDAP/Active Directory."""

    default_error_code = "ldap-error"


class OidcException(AuthenticationException):
    """Falló el descubrimiento OIDC, la obtención de JWKS o la validación del token."""

    default_error_code = "oidc-error"


class PolicyViolationException(AuthorizationException):
    """El ``Principal`` no satisface la ``Policy`` evaluada."""

    default_error_code = "policy-violation"


class InsufficientPermissionException(AuthorizationException):
    """El ``Principal`` no tiene el rol o permiso requerido."""

    default_error_code = "insufficient-permission"
