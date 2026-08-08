"""Los benchmarks de TEAF, agrupados por subsistema (Sprint 2.9.1).

Todo se mide a través de la **API pública** (`teaf.*`) salvo donde la pieza
medida es deliberadamente interna (el `ServiceContainer` resuelto por
contrato, el `ModuleRegistry` de Core) — así el propio benchmark comprueba
de paso que la superficie pública basta para construir y ejercitar el
framework.

Los benchmarks que necesitan un ciclo de vida ASGI usan `TestClient` de
Starlette: mide la cadena real de middlewares, no una simulación.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from teaf import (
    ApiAudit,
    ApiGateway,
    ApiRequestContext,
    Application,
    CapabilityCategory,
    CorsPolicy,
    Event,
    EventBus,
    GzipCompressionProvider,
    InMemoryAuditSink,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleManifest,
    OtelMeter,
    OtelTracer,
    ProtectionScope,
    RateLimiter,
    RateLimitRule,
    RequestValidator,
    ServiceContainer,
    SpanKind,
    get_logger,
)
from teaf._internal.config.settings import TestingSettings

from benchmarks.harness import BenchmarkResult, measure

#: Cada operación medida repite el trabajo este número de veces cuando una
#: sola ejecución cae por debajo de la resolución fiable del reloj (~100 ns).
#: El resultado se reporta como coste del lote, indicado en la nota.
BATCH = 1_000


class _Greeter:
    """Servicio trivial: mide el coste del contenedor, no el del servicio."""

    def greet(self) -> str:
        return "hola"


class _BenchModule(Module):
    """Módulo mínimo pero realista: un servicio, una capacidad y un evento."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="bench", name="bench", display_name="Bench")
            .with_version("1.0.0")
            .with_category(ModuleCategory.GENERIC)
            .add_service(_Greeter, lambda c: _Greeter())
            .add_capability(id="bench.greet", name="greet", category=CapabilityCategory.UTILITY)
            .add_event("bench.done")
            .build()
        )


def _demo_module() -> Module:
    return _BenchModule()


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------


def bench_startup() -> list[BenchmarkResult]:
    group = "Arranque"
    settings = TestingSettings()

    def build_application() -> None:
        Application(settings=settings)

    def full_lifecycle() -> None:
        with TestClient(Application(settings=settings).asgi):
            pass

    return [
        measure(
            "Application() (construcción)",
            build_application,
            group=group,
            repeats=20,
            measure_memory=True,
            note="factory + Runtime + registro, sin ciclo de vida",
        ),
        measure(
            "Arranque ASGI completo",
            full_lifecycle,
            group=group,
            repeats=20,
            measure_memory=True,
            note="construcción + startup + shutdown",
        ),
    ]


# ---------------------------------------------------------------------------
# Runtime, módulos y DI
# ---------------------------------------------------------------------------


def bench_runtime() -> list[BenchmarkResult]:
    group = "Runtime y módulos"
    settings = TestingSettings()

    def module_registration() -> None:
        application = Application(settings=settings, modules=[_demo_module()])
        with TestClient(application.asgi):
            pass

    application = Application(settings=settings)
    runtime = application.runtime

    def runtime_describe() -> None:
        runtime.describe()

    def diagnostics() -> None:
        runtime.diagnostics()

    return [
        measure(
            "Bootstrap de un módulo",
            module_registration,
            group=group,
            repeats=20,
            measure_memory=True,
            note="Application(modules=[...]) + ciclo de vida completo",
        ),
        measure("Runtime.describe()", runtime_describe, group=group),
        measure("Runtime.diagnostics()", diagnostics, group=group),
    ]


def bench_dependency_injection() -> list[BenchmarkResult]:
    group = "Inyección de dependencias"
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda c: _Greeter())

    transient = ServiceContainer()
    transient.register_transient(_Greeter, lambda c: _Greeter())

    scoped = ServiceContainer()
    scoped.register_scoped(_Greeter, lambda c: _Greeter())

    def resolve_singleton() -> None:
        for _ in range(BATCH):
            container.resolve(_Greeter)

    def resolve_transient() -> None:
        for _ in range(BATCH):
            transient.resolve(_Greeter)

    def resolve_scoped() -> None:
        # Un servicio SCOPED solo se resuelve dentro de un ámbito — se mide
        # el ámbito completo porque es el uso real: un ámbito por petición,
        # con varias resoluciones dentro.
        with scoped.create_scope() as scope:
            for _ in range(BATCH):
                scope.resolve(_Greeter)

    def register_service() -> None:
        fresh = ServiceContainer()
        fresh.register_singleton(_Greeter, lambda c: _Greeter())

    return [
        measure(
            "resolve() SINGLETON",
            resolve_singleton,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} resoluciones",
        ),
        measure(
            "resolve() TRANSIENT",
            resolve_transient,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} resoluciones",
        ),
        measure(
            "resolve() SCOPED",
            resolve_scoped,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} resoluciones dentro de un ámbito",
        ),
        measure("register() de un servicio", register_service, group=group),
    ]


def bench_capabilities() -> list[BenchmarkResult]:
    group = "Capacidades"
    application = Application(settings=TestingSettings(), modules=[_demo_module()])
    with TestClient(application.asgi):
        registry = application.runtime.capability_registry

        def lookup() -> None:
            for _ in range(BATCH):
                registry.find("bench.greet")

        def list_all() -> None:
            registry.list()

        return [
            measure(
                "Búsqueda de capacidad",
                lookup,
                group=group,
                repeats=20,
                note=f"lote de {BATCH:,} búsquedas",
            ),
            measure("Listado de capacidades", list_all, group=group),
        ]


def bench_event_bus() -> list[BenchmarkResult]:
    group = "Event Bus"
    bus = EventBus()
    event = Event(name="bench.event", payload={"id": 1})

    def publish_without_subscribers() -> None:
        for _ in range(BATCH):
            bus.publish(event)

    received: list[Event] = []
    subscribed = EventBus()
    subscribed.subscribe("bench.event", received.append)

    def publish_with_subscriber() -> None:
        received.clear()
        for _ in range(BATCH):
            subscribed.publish(event)

    def subscribe_and_unsubscribe() -> None:
        fresh = EventBus()
        handler: Callable[[Event], None] = received.append
        for _ in range(BATCH):
            fresh.subscribe("x", handler)
            fresh.unsubscribe("x", handler)

    return [
        measure(
            "publish() sin suscriptores",
            publish_without_subscribers,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} publicaciones",
        ),
        measure(
            "publish() con 1 suscriptor",
            publish_with_subscriber,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} publicaciones",
        ),
        measure(
            "subscribe() + unsubscribe()",
            subscribe_and_unsubscribe,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} pares",
        ),
    ]


# ---------------------------------------------------------------------------
# Observabilidad
# ---------------------------------------------------------------------------


def bench_observability() -> list[BenchmarkResult]:
    group = "Observabilidad"
    tracer = OtelTracer(TracerProvider().get_tracer("bench"))
    meter = OtelMeter(MeterProvider().get_meter("bench"))
    counter = meter.create_counter("bench.counter")
    histogram = meter.create_histogram("bench.histogram")
    logger = get_logger("bench")

    def open_span() -> None:
        for _ in range(100):
            with tracer.start_span("bench", kind=SpanKind.INTERNAL):
                pass

    def record_counter() -> None:
        for _ in range(BATCH):
            counter.add(1)

    def record_histogram() -> None:
        for _ in range(BATCH):
            histogram.record(0.5)

    def emit_log() -> None:
        for _ in range(100):
            logger.debug("bench_log", extra={"context": {"id": 1}})

    return [
        measure(
            "Abrir y cerrar un span",
            open_span,
            group=group,
            repeats=20,
            note="lote de 100 spans",
        ),
        measure(
            "Counter.add()",
            record_counter,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} registros",
        ),
        measure(
            "Histogram.record()",
            record_histogram,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} registros",
        ),
        measure(
            "Log estructurado (filtrado)",
            emit_log,
            group=group,
            repeats=20,
            note="lote de 100 logs por debajo del nivel activo",
        ),
    ]


# ---------------------------------------------------------------------------
# Protección de APIs
# ---------------------------------------------------------------------------


def _run(coroutine_factory: Callable[[], Any]) -> None:
    asyncio.run(coroutine_factory())


def bench_api_protection() -> list[BenchmarkResult]:
    group = "Protección de APIs"
    context = ApiRequestContext(client_ip="10.0.0.1", tenant_id="acme", path="/api/v1/items")

    limiter = RateLimiter(
        [RateLimitRule(name="ip", limit=10**9, window_seconds=60, scope=ProtectionScope.IP)]
    )

    async def acquire_batch() -> None:
        for _ in range(BATCH):
            await limiter.acquire(context)

    def rate_limit() -> None:
        _run(acquire_batch)

    validator = RequestValidator()
    headers = {
        "content-type": "application/json",
        "content-length": "120",
        "user-agent": "bench/1.0",
        "accept": "application/json",
        "authorization": "Bearer x",
    }

    def validate_request() -> None:
        for _ in range(BATCH):
            validator.validate_request(method="POST", url="/api/v1/items", headers=headers)

    cors = CorsPolicy(allow_origin_patterns=("https://*.torus.com",))

    def cors_headers() -> None:
        for _ in range(BATCH):
            cors.response_headers("https://app.torus.com")

    compressor = GzipCompressionProvider()
    payload = (b'{"items":[' + b'"elemento",' * 200 + b'"fin"]}') * 2

    def compress() -> None:
        for _ in range(100):
            compressor.compress(payload)

    sink = InMemoryAuditSink(limit=1000)
    audit = ApiAudit([sink])
    from teaf import build_audit_record

    record = build_audit_record(context, status_code=200, latency_seconds=0.01)

    async def audit_batch() -> None:
        for _ in range(BATCH):
            await audit.record(record)

    def record_audit() -> None:
        _run(audit_batch)

    return [
        measure(
            "RateLimiter.acquire()",
            rate_limit,
            group=group,
            repeats=10,
            note=f"lote de {BATCH:,} peticiones (ventana fija)",
        ),
        measure(
            "RequestValidator.validate_request()",
            validate_request,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} validaciones",
        ),
        measure(
            "CorsPolicy.response_headers()",
            cors_headers,
            group=group,
            repeats=20,
            note=f"lote de {BATCH:,} respuestas (comodín de subdominio)",
        ),
        measure(
            "Compresión GZip",
            compress,
            group=group,
            repeats=10,
            note=f"lote de 100 respuestas de {len(payload):,} B",
        ),
        measure(
            "ApiAudit.record()",
            record_audit,
            group=group,
            repeats=10,
            note=f"lote de {BATCH:,} registros",
        ),
    ]


# ---------------------------------------------------------------------------
# Cadena HTTP completa
# ---------------------------------------------------------------------------


def bench_http_chain() -> list[BenchmarkResult]:
    """Coste real por petición, con y sin la cadena de protección montada.

    La diferencia entre ambos es exactamente lo que cuesta proteger una API
    — el número que decide si la plataforma es asumible en producción.
    """
    group = "Cadena HTTP"

    def _application(protected: bool) -> FastAPI:
        app = FastAPI()

        @app.get("/bench")
        def endpoint() -> dict[str, str]:
            return {"status": "ok"}

        if protected:
            ApiGateway(
                rate_limiter=RateLimiter(
                    [RateLimitRule(name="ip", limit=10**9, window_seconds=60)]
                ),
                cors=CorsPolicy(allow_origins=("https://app.torus.com",)),
                validator=RequestValidator(),
                audit=ApiAudit([InMemoryAuditSink(limit=100)]),
            ).install(app)
        return app

    plain_client = TestClient(_application(protected=False))
    protected_client = TestClient(_application(protected=True))

    def plain_request() -> None:
        plain_client.get("/bench")

    def protected_request() -> None:
        protected_client.get("/bench", headers={"Origin": "https://app.torus.com"})

    return [
        measure("FastAPI sin protección", plain_request, group=group, repeats=30),
        measure(
            "FastAPI con 4 middlewares",
            protected_request,
            group=group,
            repeats=30,
            note="rate limiting + CORS + validación + auditoría",
        ),
    ]


#: Todas las suites, en el orden en que se ejecutan y se reportan.
ALL_SUITES: tuple[tuple[str, Callable[[], list[BenchmarkResult]]], ...] = (
    ("startup", bench_startup),
    ("runtime", bench_runtime),
    ("di", bench_dependency_injection),
    ("capabilities", bench_capabilities),
    ("events", bench_event_bus),
    ("observability", bench_observability),
    ("api-protection", bench_api_protection),
    ("http", bench_http_chain),
)
