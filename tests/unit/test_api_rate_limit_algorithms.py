"""Pruebas unitarias de los cuatro algoritmos de rate limiting (Sprint 2.9, ADR-009).

Los algoritmos son funciones puras sobre el estado (ver
``teaf/_internal/api/ratelimit/algorithms.py``), así que aquí se prueban sin
almacén, sin reloj real y sin dormir: ``now`` se pasa como argumento y el
estado se encadena a mano, que es exactamente lo que hace ``RateLimiter``.
"""

from __future__ import annotations

import pytest
from teaf.api import (
    FixedWindowAlgorithm,
    LeakyBucketAlgorithm,
    RateLimitAlgorithm,
    RateLimitRule,
    RateLimitState,
    SlidingWindowAlgorithm,
    TokenBucketAlgorithm,
    get_algorithm,
)

_RULE = RateLimitRule(name="test", limit=3, window_seconds=10.0)


def _drain(algorithm: object, rule: RateLimitRule, *, now: float, attempts: int) -> list[bool]:
    """Lanza ``attempts`` peticiones consecutivas en el mismo instante ``now``.

    Encadena el estado tal y como lo haría ``RateLimiter`` con un almacén
    real, pero sin I/O: cada evaluación recibe el estado que devolvió la
    anterior.
    """
    state: RateLimitState | None = None
    results: list[bool] = []
    for _ in range(attempts):
        state, decision = algorithm.evaluate(  # type: ignore[attr-defined]
            state, rule=rule, key="k", now=now, cost=1.0
        )
        results.append(decision.allowed)
    return results


@pytest.mark.parametrize(
    "algorithm",
    [
        FixedWindowAlgorithm(),
        SlidingWindowAlgorithm(),
        TokenBucketAlgorithm(),
        LeakyBucketAlgorithm(),
    ],
    ids=["fixed", "sliding", "token", "leaky"],
)
def test_every_algorithm_allows_exactly_limit_requests(algorithm: object) -> None:
    assert _drain(algorithm, _RULE, now=1000.0, attempts=5) == [True, True, True, False, False]


def test_get_algorithm_returns_one_instance_per_enum_member() -> None:
    for member in RateLimitAlgorithm:
        assert get_algorithm(member) is get_algorithm(member)


# -- Ventana fija ------------------------------------------------------------------


def test_fixed_window_resets_the_counter_when_the_window_rolls_over() -> None:
    algorithm = FixedWindowAlgorithm()
    state, _ = algorithm.evaluate(None, rule=_RULE, key="k", now=1000.0, cost=3.0)

    # 1000 y 1005 caen en la misma ventana de 10s (la que empieza en 1000).
    _, denied = algorithm.evaluate(state, rule=_RULE, key="k", now=1005.0, cost=1.0)
    assert denied.allowed is False

    # 1010 abre una ventana nueva: el contador vuelve a cero.
    _, allowed = algorithm.evaluate(state, rule=_RULE, key="k", now=1010.0, cost=1.0)
    assert allowed.allowed is True
    assert allowed.remaining == 2


def test_fixed_window_counts_rejected_requests_too() -> None:
    """Diferencia documentada con los otros tres algoritmos: aquí el contador
    avanza también con los rechazos (patrón ``INCR`` clásico)."""
    algorithm = FixedWindowAlgorithm()
    state, _ = algorithm.evaluate(None, rule=_RULE, key="k", now=1000.0, cost=3.0)
    rejected_state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)
    assert rejected_state.count == 4


def test_fixed_window_reports_time_until_the_window_closes() -> None:
    algorithm = FixedWindowAlgorithm()
    _, decision = algorithm.evaluate(None, rule=_RULE, key="k", now=1003.0, cost=1.0)
    assert decision.reset_after_seconds == pytest.approx(7.0)


# -- Ventana deslizante ------------------------------------------------------------


def test_sliding_window_only_frees_capacity_as_timestamps_leave_the_window() -> None:
    algorithm = SlidingWindowAlgorithm()
    state: RateLimitState | None = None
    for offset in (0.0, 1.0, 2.0):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0 + offset, cost=1.0)

    # A los 1009 siguen dentro las tres marcas → rechazo.
    _, denied = algorithm.evaluate(state, rule=_RULE, key="k", now=1009.0, cost=1.0)
    assert denied.allowed is False

    # A los 1010.1 ya salió la primera (1000.0) → hay hueco para una.
    _, allowed = algorithm.evaluate(state, rule=_RULE, key="k", now=1010.1, cost=1.0)
    assert allowed.allowed is True


def test_sliding_window_does_not_record_rejected_requests() -> None:
    algorithm = SlidingWindowAlgorithm()
    state: RateLimitState | None = None
    for _ in range(3):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)

    rejected_state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1001.0, cost=1.0)
    assert len(rejected_state.timestamps) == 3


def test_sliding_window_retry_after_points_at_the_oldest_excess_timestamp() -> None:
    algorithm = SlidingWindowAlgorithm()
    state: RateLimitState | None = None
    for offset in (0.0, 4.0, 8.0):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0 + offset, cost=1.0)

    _, denied = algorithm.evaluate(state, rule=_RULE, key="k", now=1009.0, cost=1.0)
    # Sobra una marca: la de 1000.0, que sale de la ventana en 1010.0.
    assert denied.retry_after_seconds == pytest.approx(1.0)


# -- Cubo de tokens ----------------------------------------------------------------


def test_token_bucket_starts_full_and_refills_over_time() -> None:
    algorithm = TokenBucketAlgorithm()
    state: RateLimitState | None = None
    for _ in range(3):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)

    _, denied = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)
    assert denied.allowed is False

    # Caudal = 3 tokens / 10 s → a los 4 s se ha repuesto algo más de un token.
    _, allowed = algorithm.evaluate(state, rule=_RULE, key="k", now=1004.0, cost=1.0)
    assert allowed.allowed is True


def test_token_bucket_never_exceeds_its_capacity() -> None:
    algorithm = TokenBucketAlgorithm()
    state, _ = algorithm.evaluate(None, rule=_RULE, key="k", now=1000.0, cost=3.0)
    # Una hora de inactividad no acumula más allá de la capacidad del cubo.
    refilled, decision = algorithm.evaluate(state, rule=_RULE, key="k", now=4600.0, cost=1.0)
    assert refilled.tokens == pytest.approx(2.0)
    assert decision.remaining == 2


def test_token_bucket_burst_allows_more_than_the_sustained_rate() -> None:
    rule = RateLimitRule(
        name="burst",
        limit=3,
        window_seconds=10.0,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst=10,
    )
    algorithm = TokenBucketAlgorithm()
    assert _drain(algorithm, rule, now=1000.0, attempts=10) == [True] * 10


def test_token_bucket_does_not_consume_tokens_when_it_rejects() -> None:
    algorithm = TokenBucketAlgorithm()
    state, _ = algorithm.evaluate(None, rule=_RULE, key="k", now=1000.0, cost=3.0)
    rejected_state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)
    assert rejected_state.tokens == pytest.approx(0.0)


# -- Cubo con fuga -----------------------------------------------------------------


def test_leaky_bucket_drains_at_a_constant_rate() -> None:
    algorithm = LeakyBucketAlgorithm()
    state: RateLimitState | None = None
    for _ in range(3):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)
    assert state is not None and state.tokens == pytest.approx(3.0)

    # Caudal de fuga = 3 / 10 s → a los 10 s el cubo está vacío.
    drained, decision = algorithm.evaluate(state, rule=_RULE, key="k", now=1010.0, cost=1.0)
    assert drained.tokens == pytest.approx(1.0)
    assert decision.allowed is True


def test_leaky_bucket_rejects_when_the_bucket_overflows() -> None:
    algorithm = LeakyBucketAlgorithm()
    state: RateLimitState | None = None
    for _ in range(3):
        state, _ = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)

    overflowed, decision = algorithm.evaluate(state, rule=_RULE, key="k", now=1000.0, cost=1.0)
    assert decision.allowed is False
    assert decision.retry_after_seconds > 0
    # El rechazo no añade trabajo a la cola.
    assert overflowed.tokens == pytest.approx(3.0)


# -- TTL del estado ----------------------------------------------------------------


def test_window_algorithms_keep_state_for_twice_the_window() -> None:
    assert FixedWindowAlgorithm().ttl_seconds(_RULE) == pytest.approx(20.0)
    assert SlidingWindowAlgorithm().ttl_seconds(_RULE) == pytest.approx(20.0)


def test_bucket_algorithms_keep_state_for_twice_the_refill_time() -> None:
    rule = RateLimitRule(name="t", limit=10, window_seconds=5.0, burst=20)
    # 20 de capacidad a 2/s → 10 s en llenarse, 20 s de TTL.
    assert TokenBucketAlgorithm().ttl_seconds(rule) == pytest.approx(20.0)
    assert LeakyBucketAlgorithm().ttl_seconds(rule) == pytest.approx(20.0)
