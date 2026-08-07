"""Proveedores distribuidos sobre Redis — **contratos preparados**, sin conectividad nativa.

Mismo criterio y mismo nivel de compromiso que
``observability/exporters/prepared.py`` (Sprint 2.8): las tres clases de
este archivo implementan por completo los contratos de
``contracts/api.py``, documentan exactamente qué comando de Redis
implementa cada operación, y **no** abren ninguna conexión — ``redis-py``
no está en [STACK.md](../../../../docs/architecture/STACK.md) y añadirlo
requeriría su propio ADR (CLAUDE.md, sección 4).

Su valor es doble y muy concreto:

1. **Demuestran que el diseño soporta Redis sin rediseño.** Cada una encaja
   en su contrato sin necesitar un solo cambio en ``RateLimiter``/
   ``QuotaManager``/``IdempotencyManager`` — que es el criterio de éxito
   explícito del Sprint 2.9 ("la arquitectura queda preparada para integrar
   Redis y gateways externos sin rediseños").
2. **Son el punto de partida real de esa integración.** Un Sprint futuro
   que apruebe ``redis-py`` por ADR solo tiene que sustituir el cuerpo de
   cada método por la llamada documentada en su docstring; ni la firma, ni
   el registro en DI, ni la configuración del módulo cambian.

Hasta entonces, construir cualquiera de ellas lanza
``NotImplementedError`` de forma explícita — nunca falla en silencio ni
finge un almacenamiento que no existe.
"""

from __future__ import annotations

from teaf._internal.api.models import IdempotencyRecord, RateLimitState
from teaf._internal.contracts.api import IdempotencyStore, QuotaStore, RateLimitStore

_UNAVAILABLE = (
    "El proveedor Redis de la plataforma de protección de APIs está preparado pero no "
    "implementado: 'redis-py' no forma parte de STACK.md y requiere un ADR aprobado "
    "(ver docs/api/API-PROTECTION.md, 'De memoria a Redis'). Usa los proveedores en "
    "memoria de teaf/_internal/api/providers/memory.py mientras tanto."
)


class _PreparedRedisProvider:
    """Base común: guarda la configuración de conexión y rechaza construirse."""

    def __init__(self, *, url: str = "redis://localhost:6379/0", prefix: str = "teaf") -> None:
        self.url = url
        self.prefix = prefix
        raise NotImplementedError(_UNAVAILABLE)


class RedisRateLimitStore(_PreparedRedisProvider, RateLimitStore):
    """``RateLimitStore`` distribuido sobre Redis (preparado).

    Implementación prevista: el ``RateLimitState`` completo cabe en un hash
    (``HSET``/``HGETALL``) con ``PEXPIRE`` para el TTL de la ventana. Para
    los cuatro algoritmos basta con eso: el estado es opaco para el almacén
    (ver ``contracts/api.py``), así que ninguna de las cuatro variantes
    necesita un tipo de dato distinto de Redis.
    """

    async def get(self, key: str) -> RateLimitState | None:
        """``HGETALL {prefix}:rl:{key}`` → ``RateLimitState`` (``None`` si no existe)."""
        raise NotImplementedError(_UNAVAILABLE)

    async def put(self, key: str, state: RateLimitState, *, ttl_seconds: float) -> None:
        """``HSET`` del estado + ``PEXPIRE`` a ``ttl_seconds``, en una única pipeline."""
        raise NotImplementedError(_UNAVAILABLE)

    async def reset(self, key: str) -> None:
        """``DEL {prefix}:rl:{key}``."""
        raise NotImplementedError(_UNAVAILABLE)


class RedisQuotaStore(_PreparedRedisProvider, QuotaStore):
    """``QuotaStore`` distribuido sobre Redis (preparado).

    Implementación prevista: ``INCRBYFLOAT`` — atómico por definición, que
    es exactamente lo que el contrato de ``consume()`` exige para evitar la
    carrera "leer, sumar, escribir" entre instancias. ``EXPIRE NX`` fija el
    vencimiento de la ventana solo la primera vez, para no prolongarla con
    cada consumo (misma semántica que ``InMemoryQuotaStore``).
    """

    async def consume(self, key: str, amount: float, *, ttl_seconds: float) -> float:
        """``INCRBYFLOAT {prefix}:q:{key} amount`` + ``EXPIRE ... NX``."""
        raise NotImplementedError(_UNAVAILABLE)

    async def peek(self, key: str) -> float:
        """``GET {prefix}:q:{key}`` (``0.0`` si no existe)."""
        raise NotImplementedError(_UNAVAILABLE)

    async def release(self, key: str, amount: float) -> float:
        """``INCRBYFLOAT {prefix}:q:{key} -amount``, acotado a 0."""
        raise NotImplementedError(_UNAVAILABLE)

    async def reset(self, key: str) -> None:
        """``DEL {prefix}:q:{key}``."""
        raise NotImplementedError(_UNAVAILABLE)


class RedisIdempotencyStore(_PreparedRedisProvider, IdempotencyStore):
    """``IdempotencyStore`` distribuido sobre Redis (preparado).

    Implementación prevista: ``SET ... PX ... NX`` con el registro
    serializado — el ``NX`` es lo que convierte "reservar la clave" en una
    operación atómica entre instancias, cerrando la ventana en la que dos
    peticiones idempotentes simultáneas podrían ejecutarse ambas.
    """

    async def get(self, key: str) -> IdempotencyRecord | None:
        """``GET {prefix}:idem:{key}`` → ``IdempotencyRecord`` deserializado."""
        raise NotImplementedError(_UNAVAILABLE)

    async def put(self, record: IdempotencyRecord) -> None:
        """``SET {prefix}:idem:{key} <record> PX <ttl>``."""
        raise NotImplementedError(_UNAVAILABLE)

    async def delete(self, key: str) -> None:
        """``DEL {prefix}:idem:{key}``."""
        raise NotImplementedError(_UNAVAILABLE)
