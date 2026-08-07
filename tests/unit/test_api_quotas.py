"""Pruebas unitarias de ``QuotaManager`` y del almacén de cuotas en memoria (Sprint 2.9).

Cubre las cuatro magnitudes de ``QuotaKind`` (peticiones, ancho de banda,
payload y concurrencia) y los cuatro períodos de ``QuotaPeriod``, que se
comportan de forma distinta a propósito — ver el docstring de
``teaf/_internal/api/quotas/manager.py``.
"""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.api.quotas.manager import build_quota_key
from teaf.api import (
    ApiRequestContext,
    InMemoryQuotaStore,
    ProtectionScope,
    QuotaKind,
    QuotaManager,
    QuotaPeriod,
    QuotaRule,
)


class _Clock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _requests_quota(limit: int = 2, period: QuotaPeriod = QuotaPeriod.DAY) -> QuotaRule:
    return QuotaRule(
        name="requests",
        kind=QuotaKind.REQUESTS,
        limit=limit,
        period=period,
        scope=ProtectionScope.TENANT,
    )


# -- Modelo ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "accumulates"),
    [
        (QuotaKind.REQUESTS, True),
        (QuotaKind.BANDWIDTH, True),
        (QuotaKind.PAYLOAD, False),
        (QuotaKind.CONCURRENT, False),
    ],
)
def test_only_requests_and_bandwidth_accumulate_over_a_window(
    kind: QuotaKind, accumulates: bool
) -> None:
    assert QuotaRule(name="q", kind=kind).accumulates is accumulates


def test_accumulating_quota_keys_carry_the_window_index() -> None:
    """Al cambiar de período cambia la clave, así el consumo arranca de cero
    sin necesitar ningún proceso de reinicio."""
    rule = _requests_quota()
    context = ApiRequestContext(tenant_id="acme")
    first = build_quota_key(rule, context, now=1_000.0)
    next_window = build_quota_key(rule, context, now=1_000.0 + 86_400.0)
    assert first != next_window


def test_concurrency_quota_keys_have_no_window_index() -> None:
    rule = QuotaRule(name="c", kind=QuotaKind.CONCURRENT, limit=2)
    context = ApiRequestContext(tenant_id="acme")
    assert build_quota_key(rule, context, now=1_000.0) == build_quota_key(
        rule, context, now=999_999.0
    )


# -- Cuotas de peticiones ---------------------------------------------------------------


def test_a_requests_quota_rejects_once_its_limit_is_reached() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=2)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")

        assert await manager.consume(context) is None
        assert await manager.consume(context) is None

        denial = await manager.consume(context)
        assert denial is not None
        assert denial.allowed is False
        assert denial.usage.remaining == 0
        assert denial.retry_after_seconds > 0

    asyncio.run(scenario())


def test_a_rejected_request_does_not_keep_counting() -> None:
    """Si el consumo desbordado se quedara sumado, el contador no bajaría
    nunca aunque el cliente dejara de insistir."""

    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")
        await manager.consume(context)

        for _ in range(5):
            denial = await manager.consume(context)
            assert denial is not None
            assert denial.usage.consumed == pytest.approx(1.0)

    asyncio.run(scenario())


def test_the_quota_resets_when_the_period_rolls_over() -> None:
    async def scenario() -> None:
        clock = _Clock()
        manager = QuotaManager([_requests_quota(limit=1, period=QuotaPeriod.HOUR)], clock=clock)
        context = ApiRequestContext(tenant_id="acme")

        assert await manager.consume(context) is None
        assert await manager.consume(context) is not None

        clock.advance(3_600.0)
        assert await manager.consume(context) is None

    asyncio.run(scenario())


@pytest.mark.parametrize("period", list(QuotaPeriod))
def test_every_period_is_enforced(period: QuotaPeriod) -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1, period=period)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")
        assert await manager.consume(context) is None
        assert await manager.consume(context) is not None

    asyncio.run(scenario())


def test_different_tenants_have_independent_quotas() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1)], clock=_Clock())
        assert await manager.consume(ApiRequestContext(tenant_id="acme")) is None
        assert await manager.consume(ApiRequestContext(tenant_id="globex")) is None
        assert await manager.consume(ApiRequestContext(tenant_id="acme")) is not None

    asyncio.run(scenario())


# -- Ancho de banda y payload -----------------------------------------------------------


def test_a_bandwidth_quota_accumulates_request_bytes() -> None:
    async def scenario() -> None:
        manager = QuotaManager(
            [QuotaRule(name="bw", kind=QuotaKind.BANDWIDTH, limit=1_000, period=QuotaPeriod.DAY)],
            clock=_Clock(),
        )
        context = ApiRequestContext(tenant_id="acme", request_bytes=400)

        assert await manager.consume(context) is None
        assert await manager.consume(context) is None

        denial = await manager.consume(context)
        assert denial is not None
        assert denial.usage.consumed == pytest.approx(800.0)

    asyncio.run(scenario())


def test_a_payload_quota_limits_a_single_request_without_accumulating() -> None:
    async def scenario() -> None:
        manager = QuotaManager(
            [QuotaRule(name="payload", kind=QuotaKind.PAYLOAD, limit=500)], clock=_Clock()
        )
        small = ApiRequestContext(tenant_id="acme", request_bytes=100)
        large = ApiRequestContext(tenant_id="acme", request_bytes=900)

        # Muchas peticiones pequeñas nunca agotan una cuota de payload.
        for _ in range(20):
            assert await manager.consume(small) is None

        denial = await manager.consume(large)
        assert denial is not None
        assert denial.retry_after_seconds == 0.0

    asyncio.run(scenario())


# -- Concurrencia ------------------------------------------------------------------------


def test_a_concurrency_quota_frees_up_on_release() -> None:
    async def scenario() -> None:
        manager = QuotaManager(
            [QuotaRule(name="conc", kind=QuotaKind.CONCURRENT, limit=1)], clock=_Clock()
        )
        context = ApiRequestContext(tenant_id="acme")

        assert await manager.consume(context) is None
        assert await manager.consume(context) is not None

        await manager.release(context)
        assert await manager.consume(context) is None

    asyncio.run(scenario())


def test_release_only_touches_concurrency_quotas() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")

        await manager.consume(context)
        await manager.release(context)
        # La cuota de peticiones sigue agotada: liberar no la devuelve.
        assert await manager.consume(context) is not None

    asyncio.run(scenario())


# -- Comportamiento general ----------------------------------------------------------------


def test_a_manager_without_rules_never_rejects() -> None:
    async def scenario() -> None:
        manager = QuotaManager()
        for _ in range(50):
            assert await manager.consume(ApiRequestContext()) is None

    asyncio.run(scenario())


def test_a_disabled_manager_never_rejects() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1)], enabled=False)
        context = ApiRequestContext(tenant_id="acme")
        assert await manager.consume(context) is None
        assert await manager.consume(context) is None

    asyncio.run(scenario())


def test_usage_reports_consumption_without_consuming() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=10)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")
        await manager.consume(context)

        for _ in range(5):
            usages = await manager.usage(context)
        assert usages[0].consumed == pytest.approx(1.0)
        assert usages[0].remaining == pytest.approx(9.0)

    asyncio.run(scenario())


def test_reset_clears_the_accumulated_consumption() -> None:
    async def scenario() -> None:
        manager = QuotaManager([_requests_quota(limit=1)], clock=_Clock())
        context = ApiRequestContext(tenant_id="acme")
        await manager.consume(context)
        assert await manager.consume(context) is not None

        await manager.reset(context)
        assert await manager.consume(context) is None

    asyncio.run(scenario())


def test_the_first_exhausted_quota_wins() -> None:
    async def scenario() -> None:
        manager = QuotaManager(
            [
                QuotaRule(
                    name="per-minute",
                    kind=QuotaKind.REQUESTS,
                    limit=1,
                    period=QuotaPeriod.MINUTE,
                    scope=ProtectionScope.TENANT,
                ),
                QuotaRule(
                    name="per-day",
                    kind=QuotaKind.REQUESTS,
                    limit=1_000,
                    period=QuotaPeriod.DAY,
                    scope=ProtectionScope.TENANT,
                ),
            ],
            clock=_Clock(),
        )
        context = ApiRequestContext(tenant_id="acme")
        await manager.consume(context)

        denial = await manager.consume(context)
        assert denial is not None and denial.usage.rule == "per-minute"

    asyncio.run(scenario())


# -- Almacén en memoria ---------------------------------------------------------------------


def test_the_quota_store_does_not_extend_a_window_on_new_traffic() -> None:
    """ "1000 al día" debe seguir siendo eso, no "1000 en 24 h sin tráfico"."""

    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryQuotaStore(clock=clock)
        await store.consume("k", 1.0, ttl_seconds=100.0)

        clock.advance(90.0)
        await store.consume("k", 1.0, ttl_seconds=100.0)
        assert await store.peek("k") == pytest.approx(2.0)

        # A los 100 s desde el primer consumo la ventana caduca igualmente.
        clock.advance(11.0)
        assert await store.peek("k") == pytest.approx(0.0)

    asyncio.run(scenario())


def test_release_never_takes_the_counter_below_zero() -> None:
    async def scenario() -> None:
        store = InMemoryQuotaStore()
        await store.consume("k", 1.0, ttl_seconds=100.0)
        assert await store.release("k", 5.0) == pytest.approx(0.0)

    asyncio.run(scenario())


def test_releasing_an_unknown_key_is_a_no_op() -> None:
    async def scenario() -> None:
        store = InMemoryQuotaStore()
        assert await store.release("missing", 1.0) == pytest.approx(0.0)

    asyncio.run(scenario())
