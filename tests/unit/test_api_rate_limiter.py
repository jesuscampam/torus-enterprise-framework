"""Pruebas unitarias de ``RateLimiter`` y del almacén en memoria (Sprint 2.9).

Aquí se prueba la capa que combina reglas, algoritmos y almacén: resolución
de dimensiones (``ProtectionScope``), filtrado por endpoint y rol,
combinación de varias reglas, e ``inspect()``/``reset()``.

Convención asíncrona: un único ``asyncio.run`` por prueba, con toda la
interacción dentro de un ``scenario()`` — igual que el resto de la suite
(``tests/unit/test_db_unit_of_work.py``). No es solo estilo: los almacenes
en memoria usan ``asyncio.Lock``, que se enlaza al primer bucle en el que se
usa, así que repartir las llamadas de un mismo almacén entre varios
``asyncio.run`` fallaría.
"""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.api.models import resolve_scope_key
from teaf._internal.api.ratelimit.limiter import build_rate_limit_key
from teaf.api import (
    ApiRequestContext,
    InMemoryRateLimitStore,
    ProtectionScope,
    RateLimitAlgorithm,
    RateLimiter,
    RateLimitRule,
    RateLimitState,
)


class _Clock:
    """Reloj controlable: las pruebas avanzan el tiempo sin dormir."""

    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# -- Resolución de dimensiones -----------------------------------------------------


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        (ProtectionScope.GLOBAL, "global"),
        (ProtectionScope.USER, "u-1"),
        (ProtectionScope.API_KEY, "key-1"),
        (ProtectionScope.TENANT, "acme"),
        (ProtectionScope.IP, "10.0.0.1"),
        (ProtectionScope.ENDPOINT, "GET /orders"),
        (ProtectionScope.ROLE, "admin"),
    ],
)
def test_resolve_scope_key_uses_the_matching_dimension(
    scope: ProtectionScope, expected: str
) -> None:
    context = ApiRequestContext(
        method="GET",
        path="/orders",
        client_ip="10.0.0.1",
        user_id="u-1",
        api_key_id="key-1",
        tenant_id="acme",
        roles=("editor", "admin"),
    )
    assert resolve_scope_key(scope, context) == expected


def test_resolve_scope_key_falls_back_when_the_dimension_is_absent() -> None:
    """Una petición sin identificar debe seguir limitándose, no colarse."""
    empty = ApiRequestContext()
    assert resolve_scope_key(ProtectionScope.USER, empty) == "anonymous"
    assert resolve_scope_key(ProtectionScope.API_KEY, empty) == "anonymous"
    assert resolve_scope_key(ProtectionScope.ROLE, empty) == "anonymous"
    assert resolve_scope_key(ProtectionScope.TENANT, empty) == "default"
    assert resolve_scope_key(ProtectionScope.IP, empty) == "unknown"


def test_resolve_scope_key_for_roles_is_stable_regardless_of_order() -> None:
    first = ApiRequestContext(roles=("viewer", "admin"))
    second = ApiRequestContext(roles=("admin", "viewer"))
    assert resolve_scope_key(ProtectionScope.ROLE, first) == resolve_scope_key(
        ProtectionScope.ROLE, second
    )


def test_build_rate_limit_key_namespaces_by_rule() -> None:
    context = ApiRequestContext(client_ip="1.1.1.1")
    per_minute = RateLimitRule(name="per-minute", limit=10, window_seconds=60)
    per_day = RateLimitRule(name="per-day", limit=1000, window_seconds=86_400)
    assert build_rate_limit_key(per_minute, context) != build_rate_limit_key(per_day, context)


# -- Filtrado de reglas --------------------------------------------------------------


def test_rules_are_filtered_by_endpoint_prefix() -> None:
    rule = RateLimitRule(name="orders", limit=1, window_seconds=60, endpoints=("/api/orders*",))
    assert rule.matches(ApiRequestContext(path="/api/orders/42")) is True
    assert rule.matches(ApiRequestContext(path="/api/customers")) is False


def test_rules_are_filtered_by_exact_endpoint_when_there_is_no_wildcard() -> None:
    rule = RateLimitRule(name="exact", limit=1, window_seconds=60, endpoints=("/api/orders",))
    assert rule.matches(ApiRequestContext(path="/api/orders")) is True
    assert rule.matches(ApiRequestContext(path="/api/orders/42")) is False


def test_rules_are_filtered_by_role() -> None:
    rule = RateLimitRule(name="free-tier", limit=1, window_seconds=60, roles=("free",))
    assert rule.matches(ApiRequestContext(roles=("free",))) is True
    assert rule.matches(ApiRequestContext(roles=("premium",))) is False


def test_capacity_and_refill_rate_derive_from_the_rule() -> None:
    without_burst = RateLimitRule(name="r", limit=10, window_seconds=5.0)
    with_burst = RateLimitRule(name="r", limit=10, window_seconds=5.0, burst=25)
    assert without_burst.capacity == 10
    assert with_burst.capacity == 25
    assert without_burst.refill_rate == pytest.approx(2.0)


# -- Comportamiento del limitador ----------------------------------------------------


def test_acquire_returns_none_while_the_request_is_allowed() -> None:
    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=2, window_seconds=60)], clock=_Clock())
        context = ApiRequestContext(client_ip="1.1.1.1")

        assert await limiter.acquire(context) is None
        assert await limiter.acquire(context) is None

        denial = await limiter.acquire(context)
        assert denial is not None
        assert denial.allowed is False
        assert denial.rule == "r"
        assert denial.retry_after_seconds > 0

    asyncio.run(scenario())


def test_a_limiter_without_rules_never_rejects() -> None:
    async def scenario() -> None:
        limiter = RateLimiter()
        for _ in range(50):
            assert await limiter.acquire(ApiRequestContext()) is None

    asyncio.run(scenario())


def test_a_disabled_limiter_never_rejects() -> None:
    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=1, window_seconds=60)], enabled=False)
        context = ApiRequestContext(client_ip="1.1.1.1")
        assert await limiter.acquire(context) is None
        assert await limiter.acquire(context) is None

    asyncio.run(scenario())


def test_different_dimension_values_are_limited_independently() -> None:
    async def scenario() -> None:
        limiter = RateLimiter(
            [RateLimitRule(name="r", limit=1, window_seconds=60, scope=ProtectionScope.TENANT)],
            clock=_Clock(),
        )
        acme = ApiRequestContext(tenant_id="acme")
        globex = ApiRequestContext(tenant_id="globex")

        assert await limiter.acquire(acme) is None
        assert await limiter.acquire(acme) is not None
        # El límite de un tenant no afecta al de otro.
        assert await limiter.acquire(globex) is None

    asyncio.run(scenario())


def test_the_first_rule_that_rejects_wins_and_stops_the_chain() -> None:
    async def scenario() -> None:
        limiter = RateLimiter(
            [
                RateLimitRule(name="strict", limit=1, window_seconds=60),
                RateLimitRule(name="loose", limit=100, window_seconds=60),
            ],
            clock=_Clock(),
        )
        context = ApiRequestContext(client_ip="1.1.1.1")
        await limiter.acquire(context)

        denial = await limiter.acquire(context)
        assert denial is not None and denial.rule == "strict"

        # La regla laxa no llegó a evaluarse en la petición rechazada: solo
        # consumió la primera, que sí pasó.
        loose = next(d for d in await limiter.inspect(context) if d.rule == "loose")
        assert loose.remaining == 99

    asyncio.run(scenario())


def test_inspect_reports_state_without_consuming_quota() -> None:
    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=5, window_seconds=60)], clock=_Clock())
        context = ApiRequestContext(client_ip="1.1.1.1")
        await limiter.acquire(context)

        for _ in range(10):
            decisions = await limiter.inspect(context)
        assert decisions[0].remaining == 4

    asyncio.run(scenario())


def test_reset_clears_the_state_of_every_applicable_rule() -> None:
    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=1, window_seconds=60)], clock=_Clock())
        context = ApiRequestContext(client_ip="1.1.1.1")
        await limiter.acquire(context)
        assert await limiter.acquire(context) is not None

        await limiter.reset(context)
        assert await limiter.acquire(context) is None

    asyncio.run(scenario())


def test_the_limit_recovers_when_the_window_advances() -> None:
    async def scenario() -> None:
        clock = _Clock()
        limiter = RateLimiter([RateLimitRule(name="r", limit=1, window_seconds=60)], clock=clock)
        context = ApiRequestContext(client_ip="1.1.1.1")

        assert await limiter.acquire(context) is None
        assert await limiter.acquire(context) is not None

        clock.advance(60.0)
        assert await limiter.acquire(context) is None

    asyncio.run(scenario())


def test_a_zero_cost_request_consumes_nothing() -> None:
    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=1, window_seconds=60)], clock=_Clock())
        context = ApiRequestContext(client_ip="1.1.1.1")
        for _ in range(5):
            assert await limiter.acquire(context, cost=0.0) is None

    asyncio.run(scenario())


@pytest.mark.parametrize("algorithm", list(RateLimitAlgorithm))
def test_every_algorithm_works_through_the_limiter(algorithm: RateLimitAlgorithm) -> None:
    async def scenario() -> None:
        limiter = RateLimiter(
            [RateLimitRule(name="r", limit=2, window_seconds=60, algorithm=algorithm)],
            clock=_Clock(),
        )
        context = ApiRequestContext(client_ip="1.1.1.1")
        assert await limiter.acquire(context) is None
        assert await limiter.acquire(context) is None
        assert await limiter.acquire(context) is not None

    asyncio.run(scenario())


def test_concurrent_requests_cannot_both_take_the_last_slot() -> None:
    """El ``asyncio.Lock`` del almacén es lo que impide que dos peticiones
    simultáneas intercalen su "leer, calcular, escribir" sobre la misma clave."""

    async def scenario() -> None:
        limiter = RateLimiter([RateLimitRule(name="r", limit=5, window_seconds=60)], clock=_Clock())
        context = ApiRequestContext(client_ip="1.1.1.1")

        results = await asyncio.gather(*(limiter.acquire(context) for _ in range(20)))
        accepted = [result for result in results if result is None]
        assert len(accepted) == 5

    asyncio.run(scenario())


# -- Almacén en memoria ---------------------------------------------------------------


def test_the_store_expires_entries_once_their_ttl_elapses() -> None:
    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryRateLimitStore(clock=clock)
        await store.put("k", RateLimitState(count=1), ttl_seconds=10.0)

        assert await store.get("k") is not None
        clock.advance(11.0)
        assert await store.get("k") is None

    asyncio.run(scenario())


def test_purge_expired_frees_keys_that_nobody_consults_again() -> None:
    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryRateLimitStore(clock=clock)
        await store.put("a", RateLimitState(count=1), ttl_seconds=10.0)
        await store.put("b", RateLimitState(count=1), ttl_seconds=1_000.0)

        clock.advance(11.0)
        assert store.purge_expired() == 1
        assert await store.get("b") is not None

    asyncio.run(scenario())


def test_reset_removes_a_key_from_the_store() -> None:
    async def scenario() -> None:
        store = InMemoryRateLimitStore()
        await store.put("k", RateLimitState(count=1), ttl_seconds=1_000.0)
        await store.reset("k")
        assert await store.get("k") is None

    asyncio.run(scenario())
