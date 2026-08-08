"""``InMemoryCacheProvider`` — caché de proceso (Sprint 3.0).

Implementación por defecto de ``CacheProvider``. Su papel es doble y ambos
importan:

1. **Es la caché real de un despliegue de una sola instancia**, que es el
   caso mayoritario en desarrollo y en muchas aplicaciones pequeñas. No
   exige infraestructura, así que TEAF funciona sin Redis.
2. **Es el doble de prueba del contrato.** Que exista permite probar el
   ciclo de vida, la expiración y el health de todo lo que consume
   ``CacheProvider`` sin depender de un servidor externo — lo que evita que
   la suite entera quede atada a que alguien levante un Redis.

Comparte el criterio de caducidad de ``api/providers/memory.py`` (Sprint
2.9.1): purga amortizada cada N escrituras, porque caducar solo al leer deja
crecer sin techo las claves que nunca se vuelven a consultar, y ese
crecimiento lo controla el tráfico, no el código.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from teaf._internal.contracts.cache import CacheProvider

#: Escrituras entre purgas completas. Mismo valor y mismo motivo que en
#: ``api/providers/memory.py``: amortizado, el coste por escritura es
#: constante y despreciable.
_PURGE_INTERVAL_WRITES = 512


@dataclass(frozen=True, slots=True)
class _Entry:
    """Valor guardado y el instante en que deja de ser válido."""

    value: bytes
    expires_at: float | None

    def is_expired(self, now: float) -> bool:
        return self.expires_at is not None and self.expires_at <= now


class InMemoryCacheProvider(CacheProvider):
    """``CacheProvider`` respaldado por un diccionario del proceso."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._connected = False
        self._writes_since_purge = 0

    # -- Ciclo de vida ---------------------------------------------------------------------

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        """Cierra y **vacía**: el estado no debe sobrevivir al apagado.

        Conservarlo haría que una aplicación reiniciada dentro del mismo
        proceso —lo que ocurre en cada prueba— heredara datos del arranque
        anterior, y eso convierte fallos reales en fallos intermitentes.
        """
        self._connected = False
        self._entries.clear()

    # -- Operaciones -----------------------------------------------------------------------

    async def get(self, key: str) -> bytes | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.is_expired(time.monotonic()):
            del self._entries[key]
            return None
        return entry.value

    async def set(self, key: str, value: bytes, *, ttl_seconds: float | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        self._entries[key] = _Entry(value=value, expires_at=expires_at)
        self._writes_since_purge += 1
        if self._writes_since_purge >= _PURGE_INTERVAL_WRITES:
            self.purge_expired()

    async def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    async def ttl(self, key: str) -> float | None:
        entry = self._entries.get(key)
        if entry is None or entry.expires_at is None:
            return None
        remaining = entry.expires_at - time.monotonic()
        return remaining if remaining > 0 else None

    async def ping(self) -> bool:
        return self._connected

    async def health_check(self) -> bool:
        return await self.ping()

    # -- Mantenimiento ---------------------------------------------------------------------

    def purge_expired(self) -> int:
        """Elimina las entradas caducadas. Devuelve cuántas se eliminaron."""
        now = time.monotonic()
        expired = [key for key, entry in self._entries.items() if entry.is_expired(now)]
        for key in expired:
            del self._entries[key]
        self._writes_since_purge = 0
        return len(expired)

    @property
    def size(self) -> int:
        """Entradas retenidas — lo que permite probar que la memoria está acotada."""
        return len(self._entries)
