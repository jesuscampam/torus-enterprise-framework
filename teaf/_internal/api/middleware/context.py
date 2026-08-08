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

Sobre la IP del cliente: es el dato del que dependen el rate limiting por
IP, las cuotas por IP y el origen registrado en auditoría, así que
resolverlo mal no es un detalle cosmético — es la diferencia entre tener y
no tener limitador. Ver ``TrustedProxies`` y ADR-011.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

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


@dataclass(frozen=True, slots=True)
class TrustedProxies:
    """Redes cuyas cabeceras de reenvío son creíbles (Sprint 3.0, ADR-011).

    ``X-Forwarded-For`` la escribe quien envía la petición, así que solo
    significa algo si quien la envía es un proxy nuestro. Este objeto
    responde a esa única pregunta —«¿viene de un proxy de confianza?»— y es
    lo que separa una cabecera informativa de una cabecera falsificable.

    Las redes se compilan **una sola vez** al construir, no en cada
    petición: el camino caliente solo hace comparaciones de pertenencia.
    Acepta IPs sueltas (``192.168.1.10``) y CIDR (``10.0.0.0/8``), en IPv4 e
    IPv6 indistintamente — ``ip_network`` trata una IP suelta como una red
    de un solo host, así que ambos casos son el mismo código.
    """

    networks: tuple[IPv4Network | IPv6Network, ...] = ()

    @classmethod
    def parse(cls, entries: Iterable[str]) -> TrustedProxies:
        """Compila ``entries`` descartando en silencio las que no sean redes válidas.

        Descartar y no lanzar es deliberado: una entrada mal escrita en una
        variable de entorno no debe impedir que la aplicación arranque, y el
        efecto de ignorarla es **más** restrictivo (ese proxy deja de ser de
        confianza), nunca menos. Fallar abierto sería el error grave; fallar
        cerrado, como aquí, solo es incómodo.
        """
        networks: list[IPv4Network | IPv6Network] = []
        for entry in entries:
            candidate = entry.strip()
            if not candidate:
                continue
            try:
                networks.append(ip_network(candidate, strict=False))
            except ValueError:
                continue
        return cls(tuple(networks))

    def __bool__(self) -> bool:
        """``True`` si hay al menos una red configurada."""
        return bool(self.networks)

    def trusts(self, candidate: str | None) -> bool:
        """``True`` si ``candidate`` pertenece a alguna de las redes de confianza."""
        if not candidate or not self.networks:
            return False
        try:
            address = ip_address(candidate.strip())
        except ValueError:
            return False
        return any(address in network for network in self.networks)


def _forwarded_chain(request: Request) -> tuple[str, ...]:
    """Entradas de ``X-Forwarded-For``/``X-Real-IP``, en el orden en que viajan."""
    for header in _FORWARDED_FOR_HEADERS:
        value = request.headers.get(header)
        if value:
            return tuple(part.strip() for part in str(value).split(",") if part.strip())
    return ()


def _connection_ip(request: Request) -> str | None:
    return str(request.client.host) if request.client is not None else None


def resolve_client_ip(
    request: Request,
    *,
    trust_forwarded_headers: bool = True,
    trusted_proxies: TrustedProxies | None = None,
) -> str | None:
    """IP del cliente, según la política de confianza configurada.

    Hay dos modos, y el primero deja sin efecto al segundo:

    1. **``trusted_proxies`` configurado** (recomendado): solo se creen las
       cabeceras de reenvío si la conexión viene de un proxy de confianza.
       Es lo que impide la falsificación desde un cliente directo.
    2. **``trusted_proxies`` vacío**: se cae al comportamiento heredado de
       ``trust_forwarded_headers`` (Sprint 2.9), que confía en la cabecera
       o no en función de un único booleano. Se mantiene por compatibilidad
       y está **deprecado** — ver ADR-011.

    ``trust_forwarded_headers`` debe ser ``False`` cuando la aplicación está
    expuesta directamente a internet y no se usa ``trusted_proxies``: un
    cliente puede falsificar ``X-Forwarded-For`` a voluntad y saltarse así
    cualquier límite por IP (ver docs/api/RATE-LIMITING.md, "Detrás de un
    proxy", y docs/security/SECURITY-CONFIGURATION.md).
    """
    connection_ip = _connection_ip(request)

    if trusted_proxies:
        if not trusted_proxies.trusts(connection_ip):
            # La petición no viene de un proxy nuestro: su cabecera de
            # reenvío no vale nada, venga como venga.
            return connection_ip
        return _client_from_chain(_forwarded_chain(request), trusted_proxies) or connection_ip

    if trust_forwarded_headers:
        chain = _forwarded_chain(request)
        if chain:
            # Modo heredado: la primera entrada es el cliente original
            # *si* toda la cadena es de confianza, cosa que este modo no
            # puede comprobar. Es justamente su limitación.
            return chain[0]
    return connection_ip


def _client_from_chain(chain: tuple[str, ...], trusted_proxies: TrustedProxies) -> str | None:
    """Primera entrada no confiable recorriendo la cadena **de derecha a izquierda**.

    El sentido del recorrido es una propiedad de seguridad, no una
    preferencia. Cada proxy *añade* a la derecha, así que la parte izquierda
    de la cadena es la que el cliente pudo escribir. Si un atacante envía
    ``X-Forwarded-For: 1.2.3.4`` y el proxy le añade su IP real, la cabecera
    que llega es ``1.2.3.4, <ip real>``: leer por la izquierda devuelve
    exactamente el valor que eligió el atacante.

    Recorriendo desde la derecha y saltando las entradas que sí son proxies
    de confianza, la primera que no lo es es el cliente real — y las
    entradas que el atacante haya inventado quedan a su izquierda, sin
    llegar a leerse nunca.
    """
    for entry in reversed(chain):
        if not trusted_proxies.trusts(entry):
            return entry
    return None


def build_request_context(
    request: Request,
    *,
    trust_forwarded_headers: bool = True,
    trusted_proxies: TrustedProxies | None = None,
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
        client_ip=resolve_client_ip(
            request,
            trust_forwarded_headers=trust_forwarded_headers,
            trusted_proxies=trusted_proxies,
        ),
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
