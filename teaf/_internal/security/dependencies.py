"""Dependencias de FastAPI para leer el ``SecurityContext`` de la petición en curso.

Cada función es una dependencia válida de cero parámetros
(``Depends(current_principal)``) — FastAPI las invoca sin inyectar nada
propio, ya que leen el ``ContextVar`` que ``SecurityMiddleware`` publicó
antes de que la petición llegara al handler (ver ``middleware.py``), no el
``Request`` en sí.
"""

from __future__ import annotations

from teaf._internal.providers.security.security_context import (
    SecurityContext,
    get_security_context,
)
from teaf._internal.security.models import ANONYMOUS_PRINCIPAL, Claims, Identity, Principal


def current_security_context() -> SecurityContext:
    """El ``SecurityContext`` completo de la petición en curso."""
    return get_security_context()


def current_principal() -> Principal:
    """El ``Principal`` de la petición en curso (anónimo si no hay autenticación)."""
    return current_security_context().principal or ANONYMOUS_PRINCIPAL


def current_identity() -> Identity:
    """La ``Identity`` de la petición en curso (anónima si no hay autenticación)."""
    return current_principal().identity


def current_claims() -> Claims:
    """Los ``Claims`` de la petición en curso (anónimos si no hay autenticación)."""
    return current_identity().claims
