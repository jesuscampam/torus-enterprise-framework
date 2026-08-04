"""Construye un ``SecurityContext`` (providers/security/, Sprint 2.2) a partir de
un ``Principal`` (security/, Sprint 2.7) — el puente entre el modelo de dominio
nuevo y el ``ContextVar`` que ya consumía cualquier router desde Sprint 2.2.
"""

from __future__ import annotations

from teaf._internal.providers.security.security_context import SecurityContext
from teaf._internal.security.models import Principal


def build_security_context(
    principal: Principal, *, correlation_id: str | None = None, request_id: str | None = None
) -> SecurityContext:
    """Traduce ``principal`` (y el correlation-id/request-id de la petición) a un
    ``SecurityContext`` listo para publicarse vía ``set_security_context()``."""
    return SecurityContext(
        principal_id=principal.id if principal.is_authenticated else None,
        roles=principal.roles,
        permissions=principal.permissions,
        identity=principal.identity,
        principal=principal,
        tenant_id=principal.tenant_id,
        provider_id=principal.identity.provider_id,
        correlation_id=correlation_id,
        request_id=request_id,
    )
