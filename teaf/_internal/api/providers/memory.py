"""Implementaciones en memoria de los contratos de almacenamiento (Sprint 2.9).

Son las implementaciones por defecto de toda la plataforma: permiten que
rate limiting, quotas, idempotencia y auditoría funcionen "de fábrica" sin
exigir ninguna infraestructura externa desplegada — mismo criterio que
``DatabaseModule`` (SQLite) o ``ObservabilityModule`` (``ConsoleExporter``).

Limitación deliberada y documentada: el estado vive en el proceso, así que
con varias instancias de la aplicación cada una aplica sus propios límites.
Para un despliegue multi-instancia se sustituyen por los proveedores
distribuidos de ``providers/redis.py`` sin tocar ninguna otra pieza (ver
docs/api/RATE-LIMITING.md, "De memoria a Redis").

Todas usan ``asyncio.Lock`` para que dos peticiones concurrentes no puedan
intercalar un "leer, calcular, escribir" sobre la misma clave — sin él, dos
peticiones simultáneas contra el mismo límite podrían pasar ambas.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable, Sequence

from teaf._internal.api.models import ApiAuditRecord, IdempotencyRecord, RateLimitState
from teaf._internal.contracts.api import (
    AuditSink,
    IdempotencyStore,
    QuotaStore,
    RateLimitStore,
)
from teaf._internal.core.logging import get_logger

#: Reloj por defecto de todos los proveedores: hora de pared en segundos.
#: Se inyecta (en vez de llamar a ``time.time()`` directamente) para que las
#: pruebas puedan avanzar el tiempo sin dormir — ver ``tests/unit/api/``.
Clock = Callable[[], float]


class InMemoryRateLimitStore(RateLimitStore):
    """Estado de rate limiting en un diccionario del proceso, con expiración perezosa."""

    def __init__(self, *, clock: Clock = time.time) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[RateLimitState, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> RateLimitState | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            state, expires_at = entry
            if expires_at <= self._clock():
                del self._entries[key]
                return None
            return state

    async def put(self, key: str, state: RateLimitState, *, ttl_seconds: float) -> None:
        async with self._lock:
            self._entries[key] = (state, self._clock() + ttl_seconds)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)

    def purge_expired(self) -> int:
        """Elimina las entradas ya expiradas y devuelve cuántas eran.

        La expiración de ``get()`` es perezosa (solo limpia lo que se
        consulta), así que una clave que deja de recibir tráfico se quedaría
        en memoria indefinidamente. Este barrido es lo que
        ``ApiProtectionModule.stop()`` ejecuta al apagar, y lo que una
        aplicación con muchísimas claves distintas puede programar
        periódicamente.
        """
        now = self._clock()
        expired = [key for key, (_, expires_at) in self._entries.items() if expires_at <= now]
        for key in expired:
            del self._entries[key]
        return len(expired)


class InMemoryQuotaStore(QuotaStore):
    """Consumo de cuotas en un diccionario del proceso, con expiración perezosa."""

    def __init__(self, *, clock: Clock = time.time) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    def _read(self, key: str) -> float:
        """Consumo vigente de ``key`` (``0.0`` si no existe o ya expiró). Requiere el lock."""
        entry = self._entries.get(key)
        if entry is None:
            return 0.0
        consumed, expires_at = entry
        if expires_at <= self._clock():
            del self._entries[key]
            return 0.0
        return consumed

    async def consume(self, key: str, amount: float, *, ttl_seconds: float) -> float:
        async with self._lock:
            total = self._read(key) + amount
            # Conserva el vencimiento original de la ventana si ya existía: una
            # ventana de cuota no se prolonga porque llegue tráfico nuevo (eso
            # convertiría "1000 al día" en "1000 en 24h sin tráfico").
            entry = self._entries.get(key)
            expires_at = entry[1] if entry is not None else self._clock() + ttl_seconds
            self._entries[key] = (total, expires_at)
            return total

    async def peek(self, key: str) -> float:
        async with self._lock:
            return self._read(key)

    async def release(self, key: str, amount: float) -> float:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 0.0
            total = max(0.0, entry[0] - amount)
            self._entries[key] = (total, entry[1])
            return total

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)


class InMemoryIdempotencyStore(IdempotencyStore):
    """Respuestas idempotentes en un diccionario del proceso, expiradas por ``expires_at``."""

    def __init__(self, *, clock: Clock = time.time) -> None:
        self._clock = clock
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> IdempotencyRecord | None:
        async with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            if record.expires_at <= self._clock():
                del self._records[key]
                return None
            return record

    async def put(self, record: IdempotencyRecord) -> None:
        async with self._lock:
            self._records[record.key] = record

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._records.pop(key, None)


class InMemoryAuditSink(AuditSink):
    """Destino de auditoría en memoria, con historial acotado.

    Pensado para desarrollo, pruebas y para inspeccionar la auditoría desde
    el propio proceso (``sink.records``). En producción se combina con
    ``LoggingAuditSink`` —o con un destino propio hacia una tabla de
    auditoría/SIEM— sin que ``ApiAudit`` cambie: acepta varios destinos.
    """

    def __init__(self, *, limit: int = 1_000) -> None:
        self._records: deque[ApiAuditRecord] = deque(maxlen=limit)

    @property
    def name(self) -> str:
        return "memory"

    async def emit(self, record: ApiAuditRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> Sequence[ApiAuditRecord]:
        """Registros retenidos, del más antiguo al más reciente."""
        return tuple(self._records)

    def clear(self) -> None:
        """Vacía el historial retenido."""
        self._records.clear()


class LoggingAuditSink(AuditSink):
    """Destino de auditoría que emite cada registro como log estructurado.

    Se apoya en ``core/logging.py`` (Sprint 2.8): con ``log_format="json"``
    cada entrada sale como una línea JSON con correlation/trace/span-id ya
    incluidos, lista para que la recoja cualquier agente de logs — es la
    integración más directa entre auditoría y observabilidad, sin acoplar
    ``ApiAudit`` a ningún exportador concreto.
    """

    def __init__(self, *, logger_name: str = "teaf.api.audit") -> None:
        self._logger = get_logger(logger_name)

    @property
    def name(self) -> str:
        return "logging"

    async def emit(self, record: ApiAuditRecord) -> None:
        self._logger.info("api_audit_record", extra={"context": record.as_dict()})
