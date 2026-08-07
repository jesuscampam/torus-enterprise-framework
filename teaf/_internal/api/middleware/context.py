"""``build_request_context`` — traduce una petición ASGI a ``ApiRequestContext``.

El único punto de todo el subsistema que conoce Starlette. Todo lo demás
(limitador, cuotas, auditoría) trabaja sobre ``ApiRequestContext``, que es
un dato puro — por eso la plataforma se puede probar entera sin servidor y
reutilizar desde un worker o un consumidor de cola.

Sobre la identidad: se lee del ``SecurityContext`` que ``SecurityMiddleware``
(Sprint 2.7) ya dejó resuelto. Si esa resolución aún no ha ocurrido —porque
los middlewares de protección quedaron por fuera de él, ver
``ApiGateway.install``— el contexto es el anónimo por defecto y la
plataforma limita por IP en vez de por usuario, que es exactamente el
comportamiento correcto para tráfico sin identificar.
"""

from __future__ import annotations

from starlette.requests import Request

from teaf._internal.api.models import ApiRequestContext
from teaf._internal.core.context import (
    NO_CORRELATION_ID,
    get_correlation_id,
    get_span_id,
    get_trace_id,
)
from teaf._internal.providers.security.security_context import get_security_context
from teaf._internal.shared.constants import HEADER_CORRELATION_ID

#: Cabeceras que un proxy inverso usa para propagar la IP real del cliente,
#: en orden de preferencia. Sin ellas, todas las peticiones detrás de un
#: balanceador compartirían la IP del propio balanceador y cualquier límite
#: por IP se volvería un límite global.
_FORWARDED_FOR_HEADERS = ("X-Forwarded-For", "X-Real-IP")


def resolve_client_ip(request: Request, *, trust_forwarded_headers: bool = True) -> str | None:
    """IP del cliente, respetando las cabeceras de proxy si se confía en ellas.

    ``trust_forwarded_headers`` debe ser ``False`` cuando la aplicación está
    expuesta directamente a internet: un cliente puede falsificar
    ``X-Forwarded-For`` a voluntad y saltarse así cualquier límite por IP.
    Solo tiene sentido confiar en ellas detrás de un proxy que las
    reescriba (ver docs/api/RATE-LIMITING.md, "Detrás de un proxy").
    """
    if trust_forwarded_headers:
        for header in _FORWARDED_FOR_HEADERS:
            value = request.headers.get(header)
            if value:
                # X-Forwarded-For es una lista "cliente, proxy1, proxy2":
                # el primero es el cliente original.
                return str(value).split(",")[0].strip()
    return str(request.client.host) if request.client is not None else None


def build_request_context(
    request: Request, *, trust_forwarded_headers: bool = True
) -> ApiRequestContext:
    """Construye el ``ApiRequestContext`` de ``request``."""
    security = get_security_context()

    correlation_id = get_correlation_id()
    if correlation_id == NO_CORRELATION_ID:
        # ``RequestIdMiddleware`` todavía no ha corrido (los middlewares de
        # protección quedan por fuera de él, ver ``ApiGateway.install``): se
        # cae a la cabecera entrante, que es la misma que ese middleware
        # habría propagado.
        correlation_id = request.headers.get(HEADER_CORRELATION_ID) or NO_CORRELATION_ID

    content_length = request.headers.get("content-length")
    api_key_id = security.identity.id if security.identity is not None else None

    return ApiRequestContext(
        method=request.method,
        path=request.url.path,
        client_ip=resolve_client_ip(request, trust_forwarded_headers=trust_forwarded_headers),
        user_id=security.principal_id,
        api_key_id=api_key_id if security.provider_id == "api-key" else None,
        tenant_id=security.tenant_id,
        roles=tuple(sorted(role.name for role in security.roles)),
        request_bytes=int(content_length) if content_length and content_length.isdigit() else 0,
        correlation_id=None if correlation_id == NO_CORRELATION_ID else correlation_id,
        trace_id=get_trace_id(),
        span_id=get_span_id(),
        user_agent=request.headers.get("user-agent"),
    )
