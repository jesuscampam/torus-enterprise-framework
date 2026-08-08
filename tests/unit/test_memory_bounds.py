"""Pruebas de acotación de memoria de los almacenes en memoria (Sprint 2.9.1).

Estas pruebas existen por un defecto real encontrado en la auditoría de
producción del Sprint 2.9.1: los tres almacenes expiraban **solo de forma
perezosa** (una entrada desaparecía únicamente cuando alguien volvía a
consultar esa misma clave), así que crecían con la *cardinalidad* del
tráfico y no con el tráfico concurrente. Con rate limiting por IP en una API
pública eso es una fuga: cada IP que llama una vez y no vuelve deja su
entrada retenida para siempre.

Cada prueba de aquí abajo reproduce ese escenario —muchas claves distintas,
cada una vista una sola vez— y comprueba que el diccionario queda acotado
por las claves *vivas* y no por las *vistas*.
"""

from __future__ import annotations

import asyncio

from teaf._internal.api.providers.memory import _PURGE_INTERVAL_WRITES
from teaf.api import (
    ApiRequestContext,
    InMemoryIdempotencyStore,
    InMemoryQuotaStore,
    InMemoryRateLimitStore,
    ProtectionScope,
    RateLimiter,
    RateLimitRule,
    RateLimitState,
)


class _Clock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


#: Claves distintas a escribir. Por encima del umbral de barrido, para que la
#: prueba ejercite el camino automático y no solo el manual.
_UNIQUE_KEYS = _PURGE_INTERVAL_WRITES * 3


def test_the_rate_limit_store_does_not_grow_with_keys_that_never_return() -> None:
    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryRateLimitStore(clock=clock)

        # Cada clave se escribe una sola vez y ya nace expirada en cuanto
        # avanza el reloj — el escenario de "una IP que llama y no vuelve".
        for index in range(_UNIQUE_KEYS):
            clock.advance(1.0)
            await store.put(f"ip:{index}", RateLimitState(count=1), ttl_seconds=10.0)

        # Sin barrido automático, aquí habría _UNIQUE_KEYS entradas.
        assert store.size < _PURGE_INTERVAL_WRITES * 2
        # Y lo que queda es solo lo aún vivo (ventana de 10 s a 1 s por clave).
        assert store.purge_expired() >= 0
        clock.advance(100.0)
        store.purge_expired()
        assert store.size == 0

    asyncio.run(scenario())


def test_the_quota_store_does_not_grow_with_closed_windows() -> None:
    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryQuotaStore(clock=clock)

        for index in range(_UNIQUE_KEYS):
            clock.advance(1.0)
            await store.consume(f"tenant:{index}", 1.0, ttl_seconds=10.0)

        assert store.size < _PURGE_INTERVAL_WRITES * 2
        clock.advance(100.0)
        store.purge_expired()
        assert store.size == 0

    asyncio.run(scenario())


def test_the_idempotency_store_does_not_grow_with_single_use_keys() -> None:
    """El más propenso a crecer: TTL de 24 h y el cuerpo de la respuesta dentro."""

    async def scenario() -> None:
        from teaf.api import IdempotencyManager

        clock = _Clock()
        store = InMemoryIdempotencyStore(clock=clock)
        manager = IdempotencyManager(store=store, ttl_seconds=10.0, clock=clock)

        for index in range(_UNIQUE_KEYS):
            clock.advance(1.0)
            await manager.remember(
                f"key:{index}", fingerprint="fp", status_code=201, body=b'{"id":1}'
            )

        assert store.size < _PURGE_INTERVAL_WRITES * 2
        clock.advance(100.0)
        store.purge_expired()
        assert store.size == 0

    asyncio.run(scenario())


def test_live_entries_survive_the_automatic_purge() -> None:
    """El barrido no puede llevarse por delante estado todavía vigente."""

    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryRateLimitStore(clock=clock)

        await store.put("vive", RateLimitState(count=1), ttl_seconds=10_000.0)
        for index in range(_PURGE_INTERVAL_WRITES + 10):
            await store.put(f"efimera:{index}", RateLimitState(count=1), ttl_seconds=0.0)
            clock.advance(0.001)

        assert await store.get("vive") is not None

    asyncio.run(scenario())


def test_a_rate_limited_api_stays_bounded_across_many_distinct_clients() -> None:
    """La prueba de integración del escenario real: limitar por IP a miles de
    clientes distintos no puede hacer crecer la memoria sin techo."""

    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryRateLimitStore(clock=clock)
        limiter = RateLimiter(
            [RateLimitRule(name="ip", limit=10, window_seconds=60, scope=ProtectionScope.IP)],
            store=store,
            clock=clock,
        )

        for index in range(_UNIQUE_KEYS):
            clock.advance(1.0)
            await limiter.acquire(ApiRequestContext(client_ip=f"10.0.{index // 256}.{index % 256}"))

        # Con ventanas de 60 s y una petición por segundo, solo unas decenas de
        # claves siguen vivas — el resto ya se barrió sola.
        assert store.size < _PURGE_INTERVAL_WRITES * 2

    asyncio.run(scenario())
