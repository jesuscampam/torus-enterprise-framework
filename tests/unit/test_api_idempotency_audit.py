"""Pruebas unitarias de ``IdempotencyManager`` y ``ApiAudit`` (Sprint 2.9)."""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.runtime.event_bus import Event, EventBus
from teaf.api import (
    ApiAudit,
    ApiAuditRecord,
    ApiOutcome,
    ApiRequestContext,
    AuditSink,
    IdempotencyConflictException,
    IdempotencyManager,
    InMemoryAuditSink,
    InMemoryIdempotencyStore,
    LoggingAuditSink,
    build_audit_record,
    build_fingerprint,
)


class _Clock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# -- Idempotencia: huella ---------------------------------------------------------------


def test_the_fingerprint_changes_with_method_path_and_body() -> None:
    base = build_fingerprint(method="POST", path="/orders", body=b'{"sku":"A"}')
    assert base != build_fingerprint(method="PATCH", path="/orders", body=b'{"sku":"A"}')
    assert base != build_fingerprint(method="POST", path="/carts", body=b'{"sku":"A"}')
    assert base != build_fingerprint(method="POST", path="/orders", body=b'{"sku":"B"}')


def test_the_fingerprint_is_stable_for_the_same_request() -> None:
    first = build_fingerprint(method="POST", path="/orders", body=b"payload")
    second = build_fingerprint(method="post", path="/orders", body=b"payload")
    assert first == second


# -- Idempotencia: gestor ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "applies"),
    [("POST", True), ("PATCH", True), ("GET", False), ("PUT", False), ("DELETE", False)],
)
def test_idempotency_only_applies_to_non_idempotent_methods(method: str, applies: bool) -> None:
    """GET/PUT/DELETE ya son idempotentes por definición de HTTP."""
    assert IdempotencyManager().applies_to(method) is applies


def test_a_disabled_manager_applies_to_nothing() -> None:
    assert IdempotencyManager(enabled=False).applies_to("POST") is False


def test_the_first_request_with_a_key_finds_no_previous_response() -> None:
    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        assert await manager.lookup("k1", fingerprint="fp") is None

    asyncio.run(scenario())


def test_a_retry_with_the_same_body_replays_the_stored_response() -> None:
    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        await manager.remember(
            "k1",
            fingerprint="fp",
            status_code=201,
            body=b'{"id":"abc"}',
            headers={"content-type": "application/json"},
        )

        record = await manager.lookup("k1", fingerprint="fp")
        assert record is not None
        assert record.status_code == 201
        assert record.body == b'{"id":"abc"}'

    asyncio.run(scenario())


def test_reusing_a_key_with_a_different_body_is_a_conflict() -> None:
    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        await manager.remember("k1", fingerprint="fp-a", status_code=201, body=b"{}")

        with pytest.raises(IdempotencyConflictException) as exc_info:
            await manager.lookup("k1", fingerprint="fp-b")
        assert exc_info.value.http_status == 409

    asyncio.run(scenario())


def test_server_errors_are_never_remembered() -> None:
    """Cachear un 500 condenaría al cliente a recibirlo durante todo el TTL,
    incluso cuando la causa ya estuviera resuelta."""

    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        assert await manager.remember("k1", fingerprint="fp", status_code=500, body=b"") is None
        assert await manager.lookup("k1", fingerprint="fp") is None

    asyncio.run(scenario())


def test_client_errors_are_remembered() -> None:
    """Un 400 sí es determinista: reintentar la misma petición dará el mismo 400."""

    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        await manager.remember("k1", fingerprint="fp", status_code=400, body=b"bad")
        record = await manager.lookup("k1", fingerprint="fp")
        assert record is not None and record.status_code == 400

    asyncio.run(scenario())


def test_a_stored_response_expires_after_its_ttl() -> None:
    async def scenario() -> None:
        clock = _Clock()
        manager = IdempotencyManager(ttl_seconds=60.0, clock=clock)
        await manager.remember("k1", fingerprint="fp", status_code=200, body=b"ok")

        clock.advance(61.0)
        assert await manager.lookup("k1", fingerprint="fp") is None

    asyncio.run(scenario())


def test_forget_removes_a_stored_response() -> None:
    async def scenario() -> None:
        manager = IdempotencyManager(clock=_Clock())
        await manager.remember("k1", fingerprint="fp", status_code=200, body=b"ok")
        await manager.forget("k1")
        assert await manager.lookup("k1", fingerprint="fp") is None

    asyncio.run(scenario())


def test_the_idempotency_store_deletes_expired_records_on_read() -> None:
    async def scenario() -> None:
        clock = _Clock()
        store = InMemoryIdempotencyStore(clock=clock)
        manager = IdempotencyManager(store=store, ttl_seconds=10.0, clock=clock)
        await manager.remember("k1", fingerprint="fp", status_code=200, body=b"ok")

        clock.advance(11.0)
        assert await store.get("k1") is None

    asyncio.run(scenario())


# -- Auditoría ------------------------------------------------------------------------------


def _context() -> ApiRequestContext:
    return ApiRequestContext(
        method="POST",
        path="/api/v1/orders",
        client_ip="10.0.0.1",
        user_id="u-1",
        api_key_id="key-1",
        tenant_id="acme",
        request_bytes=120,
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )


def test_an_audit_record_carries_every_field_the_sprint_requires() -> None:
    record = build_audit_record(
        _context(), status_code=201, latency_seconds=0.25, response_bytes=340, api_version="v1"
    )
    payload = record.as_dict()

    for field in (
        "method",
        "path",
        "statusCode",
        "latencySeconds",
        "identityId",
        "tenantId",
        "apiKeyId",
        "correlationId",
        "traceId",
        "spanId",
        "clientIp",
        "apiVersion",
        "requestBytes",
        "responseBytes",
        "outcome",
        "recordedAt",
    ):
        assert field in payload, field
    assert payload["identityId"] == "u-1"
    assert payload["traceId"] == "trace-1"


def test_records_reach_every_configured_sink() -> None:
    async def scenario() -> None:
        first, second = InMemoryAuditSink(), InMemoryAuditSink()
        audit = ApiAudit([first, second])
        await audit.record(build_audit_record(_context(), status_code=200, latency_seconds=0.1))

        assert len(first.records) == 1
        assert len(second.records) == 1

    asyncio.run(scenario())


def test_a_failing_sink_does_not_stop_the_others() -> None:
    """Perder una API entera porque un SIEM está caído sería peor que perder
    una entrada de auditoría en ese destino."""

    class _BrokenSink(AuditSink):
        @property
        def name(self) -> str:
            return "broken"

        async def emit(self, record: ApiAuditRecord) -> None:
            raise RuntimeError("SIEM caído")

    async def scenario() -> None:
        healthy = InMemoryAuditSink()
        audit = ApiAudit([_BrokenSink(), healthy])
        await audit.record(build_audit_record(_context(), status_code=200, latency_seconds=0.1))
        assert len(healthy.records) == 1

    asyncio.run(scenario())


def test_recording_publishes_the_audit_event() -> None:
    async def scenario() -> None:
        bus = EventBus()
        seen: list[Event] = []
        bus.subscribe("audit.recorded", seen.append)

        audit = ApiAudit([InMemoryAuditSink()], event_bus=bus)
        await audit.record(build_audit_record(_context(), status_code=200, latency_seconds=0.1))

        assert len(seen) == 1
        assert seen[0].payload["statusCode"] == 200

    asyncio.run(scenario())


def test_a_disabled_audit_records_nothing() -> None:
    async def scenario() -> None:
        sink = InMemoryAuditSink()
        audit = ApiAudit([sink], enabled=False)
        await audit.record(build_audit_record(_context(), status_code=200, latency_seconds=0.1))
        assert sink.records == ()

    asyncio.run(scenario())


def test_an_audit_without_sinks_still_works() -> None:
    """Una auditoría mal configurada nunca debe tumbar la API que audita."""

    async def scenario() -> None:
        bus = EventBus()
        seen: list[Event] = []
        bus.subscribe("audit.recorded", seen.append)

        audit = ApiAudit(event_bus=bus)
        await audit.record(build_audit_record(_context(), status_code=200, latency_seconds=0.1))
        assert len(seen) == 1

    asyncio.run(scenario())


def test_the_memory_sink_keeps_a_bounded_history() -> None:
    async def scenario() -> None:
        sink = InMemoryAuditSink(limit=3)
        for index in range(10):
            await sink.emit(
                build_audit_record(_context(), status_code=200 + index, latency_seconds=0.1)
            )
        assert len(sink.records) == 3
        assert sink.records[-1].status_code == 209

        sink.clear()
        assert sink.records == ()

    asyncio.run(scenario())


def test_the_logging_sink_emits_without_failing() -> None:
    async def scenario() -> None:
        sink = LoggingAuditSink()
        assert sink.name == "logging"
        await sink.emit(build_audit_record(_context(), status_code=200, latency_seconds=0.1))

    asyncio.run(scenario())


@pytest.mark.parametrize("outcome", list(ApiOutcome))
def test_every_outcome_serialises(outcome: ApiOutcome) -> None:
    record = build_audit_record(_context(), status_code=200, latency_seconds=0.1, outcome=outcome)
    assert record.as_dict()["outcome"] == outcome.value
