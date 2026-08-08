"""Pruebas de integración HTTP de la plataforma de protección de APIs (Sprint 2.9).

Aquí se prueba lo que las unitarias no pueden: los ocho middlewares
aplicándose sobre peticiones reales, en el orden que fija ``ApiGateway``, y
su convivencia con los middlewares propios del framework
(``RequestIdMiddleware``/``RequestLoggingMiddleware``) y con
``SecurityMiddleware``/``ObservabilityMiddleware`` de los Sprints 2.7 y 2.8.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf import Application
from teaf._internal.config.settings import TestingSettings
from teaf._internal.runtime.event_bus import Event
from teaf.api import (
    ApiAudit,
    ApiGateway,
    ApiProtectionConfiguration,
    ApiProtectionModule,
    ApiVersion,
    ApiVersioningPolicy,
    ApiVersionNegotiator,
    CompressionNegotiator,
    CompressionPolicy,
    CorsPolicy,
    GzipCompressionProvider,
    IdempotencyManager,
    InMemoryAuditSink,
    ProtectionScope,
    QuotaKind,
    QuotaManager,
    QuotaRule,
    RateLimiter,
    RateLimitRule,
    RequestValidationPolicy,
    RequestValidator,
)

_ORIGIN = "https://app.torus.com"


def _routed_app() -> FastAPI:
    """Aplicación mínima con los verbos que necesita esta suite."""
    app = FastAPI()
    counter = {"value": 0}

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "ok"}

    @app.get("/api/v1/items")
    def items() -> dict[str, object]:
        return {"items": ["elemento-de-relleno" for _ in range(80)]}

    @app.post("/api/v1/orders")
    def create_order() -> dict[str, int]:
        counter["value"] += 1
        return {"sequence": counter["value"]}

    @app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("fallo del endpoint")

    return app


# -- Rate limiting -------------------------------------------------------------------


def test_a_request_over_the_limit_gets_429_with_rfc7807_and_retry_after() -> None:
    app = _routed_app()
    ApiGateway(
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=2, window_seconds=60)])
    ).install(app)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200

    response = client.get("/ping")
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1

    problem = response.json()
    assert problem["type"] == "https://teaf.torus/errors/rate-limit-exceeded"
    assert problem["status"] == 429
    assert problem["instance"] == "/ping"


def test_rate_limit_headers_travel_on_accepted_responses_too() -> None:
    """Un cliente bien educado se autorregula con ``X-RateLimit-Remaining``
    antes de chocar — y solo puede si viaja también en las respuestas OK."""
    app = _routed_app()
    ApiGateway(
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=5, window_seconds=60)])
    ).install(app)
    client = TestClient(app)

    response = client.get("/ping")
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"


def test_the_tightest_rule_is_the_one_reported() -> None:
    app = _routed_app()
    ApiGateway(
        rate_limiter=RateLimiter(
            [
                RateLimitRule(name="loose", limit=1_000, window_seconds=60),
                RateLimitRule(name="tight", limit=10, window_seconds=60),
            ]
        )
    ).install(app)

    response = TestClient(app).get("/ping")
    assert response.headers["X-RateLimit-Limit"] == "10"


def test_the_limit_is_applied_per_client_ip() -> None:
    app = _routed_app()
    ApiGateway(
        rate_limiter=RateLimiter(
            [RateLimitRule(name="ip", limit=1, window_seconds=60, scope=ProtectionScope.IP)]
        )
    ).install(app)
    client = TestClient(app)

    assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    # Otra IP tiene su propio presupuesto.
    assert client.get("/ping", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200


def test_forwarded_headers_can_be_distrusted() -> None:
    """Expuesta directamente a internet, ``X-Forwarded-For`` la controla el
    cliente: confiar en ella dejaría saltarse cualquier límite por IP."""
    app = _routed_app()
    ApiGateway(
        rate_limiter=RateLimiter(
            [RateLimitRule(name="ip", limit=1, window_seconds=60, scope=ProtectionScope.IP)]
        ),
        trust_forwarded_headers=False,
    ).install(app)
    client = TestClient(app)

    assert client.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    # Cambiar la cabecera ya no cambia la clave: sigue siendo la misma IP real.
    assert client.get("/ping", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 429


# -- Quotas ---------------------------------------------------------------------------


def test_an_exhausted_quota_gets_429_with_quota_headers() -> None:
    app = _routed_app()
    ApiGateway(
        quota_manager=QuotaManager([QuotaRule(name="daily", limit=1, scope=ProtectionScope.TENANT)])
    ).install(app)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200

    response = client.get("/ping")
    assert response.status_code == 429
    assert response.headers["X-Quota-Limit"] == "1"
    assert response.headers["X-Quota-Remaining"] == "0"
    assert response.json()["type"] == "https://teaf.torus/errors/quota-exceeded"


def test_a_concurrency_quota_is_released_even_when_the_endpoint_fails() -> None:
    """Sin el ``finally`` de ``QuotaMiddleware``, el contador se quedaría alto
    y la cuota se agotaría sola tras suficientes errores."""
    app = _routed_app()
    ApiGateway(
        quota_manager=QuotaManager([QuotaRule(name="conc", kind=QuotaKind.CONCURRENT, limit=1)])
    ).install(app)
    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/boom").status_code == 500
    # La concurrencia se liberó: la siguiente petición pasa.
    assert client.get("/ping").status_code == 200


# -- CORS ------------------------------------------------------------------------------


def test_a_preflight_from_an_allowed_origin_is_answered_with_204() -> None:
    app = _routed_app()
    ApiGateway(cors=CorsPolicy(allow_origins=(_ORIGIN,), allow_credentials=True)).install(app)

    response = TestClient(app).options(
        "/ping",
        headers={"Origin": _ORIGIN, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == _ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_a_preflight_from_a_disallowed_origin_is_rejected_without_cors_headers() -> None:
    app = _routed_app()
    ApiGateway(cors=CorsPolicy(allow_origins=(_ORIGIN,))).install(app)

    response = TestClient(app).options(
        "/ping",
        headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_cors_headers_accompany_error_responses_too() -> None:
    """Un 429 sin cabeceras CORS lo oculta el navegador como error de red
    genérico: el desarrollador ve "failed to fetch" en vez del motivo real."""
    app = _routed_app()
    ApiGateway(
        cors=CorsPolicy(allow_origins=(_ORIGIN,)),
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=1, window_seconds=60)]),
    ).install(app)
    client = TestClient(app)

    client.get("/ping", headers={"Origin": _ORIGIN})
    response = client.get("/ping", headers={"Origin": _ORIGIN})
    assert response.status_code == 429
    assert response.headers["Access-Control-Allow-Origin"] == _ORIGIN


def test_a_request_without_origin_passes_untouched() -> None:
    app = _routed_app()
    ApiGateway(cors=CorsPolicy(allow_origins=(_ORIGIN,))).install(app)

    response = TestClient(app).get("/ping")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


# -- Versionado --------------------------------------------------------------------------


def _versioned_gateway(**overrides: object) -> ApiGateway:
    policy_args: dict[str, object] = {
        "supported": (ApiVersion(1), ApiVersion(2)),
        "default": ApiVersion(1),
    }
    policy_args.update(overrides)
    return ApiGateway(
        versioning=ApiVersionNegotiator(ApiVersioningPolicy(**policy_args))  # type: ignore[arg-type]
    )


def test_the_served_version_is_reported_in_the_response() -> None:
    app = _routed_app()
    _versioned_gateway().install(app)

    response = TestClient(app).get("/api/v1/items")
    assert response.headers["X-API-Version"] == "v1"


def test_the_version_can_be_requested_by_header() -> None:
    app = _routed_app()
    _versioned_gateway().install(app)

    response = TestClient(app).get("/ping", headers={"X-API-Version": "2"})
    assert response.headers["X-API-Version"] == "v2"


def test_the_version_can_be_requested_by_media_type() -> None:
    app = _routed_app()
    _versioned_gateway().install(app)

    response = TestClient(app).get("/ping", headers={"Accept": "application/vnd.teaf.v2+json"})
    assert response.headers["X-API-Version"] == "v2"


def test_an_unsupported_version_gets_400() -> None:
    app = _routed_app()
    _versioned_gateway().install(app)

    response = TestClient(app).get("/ping", headers={"X-API-Version": "9"})
    assert response.status_code == 400
    assert response.json()["type"] == "https://teaf.torus/errors/unsupported-api-version"


def test_a_deprecated_version_carries_deprecation_and_sunset_headers() -> None:
    app = _routed_app()
    _versioned_gateway(deprecated={"v1": "Wed, 31 Dec 2026 23:59:59 GMT"}).install(app)

    response = TestClient(app).get("/api/v1/items")
    assert response.headers["Deprecation"] == "true"
    assert response.headers["Sunset"] == "Wed, 31 Dec 2026 23:59:59 GMT"


# -- Validación ---------------------------------------------------------------------------


def test_an_oversized_body_gets_413() -> None:
    app = _routed_app()
    ApiGateway(validator=RequestValidator(RequestValidationPolicy(max_request_bytes=50))).install(
        app
    )

    response = TestClient(app).post("/api/v1/orders", json={"payload": "x" * 500})
    assert response.status_code == 413
    assert response.json()["type"] == "https://teaf.torus/errors/request-too-large"


def test_a_forbidden_content_type_gets_415() -> None:
    app = _routed_app()
    ApiGateway(
        validator=RequestValidator(
            RequestValidationPolicy(allowed_content_types=("application/json",))
        )
    ).install(app)

    response = TestClient(app).post(
        "/api/v1/orders", content=b"<xml/>", headers={"Content-Type": "application/xml"}
    )
    assert response.status_code == 415


def test_an_oversized_response_is_caught_when_response_validation_is_on() -> None:
    """No es un error del cliente: la petición era válida y fue el servidor
    quien produjo una respuesta fuera del contrato declarado."""
    app = _routed_app()
    ApiGateway(
        validator=RequestValidator(RequestValidationPolicy(max_response_bytes=50)),
        validate_responses=True,
    ).install(app)

    response = TestClient(app).get("/api/v1/items")
    assert response.status_code == 500
    assert response.json()["type"] == "https://teaf.torus/errors/response-too-large"


def test_response_validation_lets_a_small_response_through_intact() -> None:
    app = _routed_app()
    ApiGateway(
        validator=RequestValidator(RequestValidationPolicy(max_response_bytes=10_000)),
        validate_responses=True,
    ).install(app)

    response = TestClient(app).get("/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "ok"}


def test_a_missing_required_header_gets_400() -> None:
    app = _routed_app()
    ApiGateway(
        validator=RequestValidator(RequestValidationPolicy(required_headers=("X-Tenant",)))
    ).install(app)
    client = TestClient(app)

    assert client.get("/ping").status_code == 400
    assert client.get("/ping", headers={"X-Tenant": "acme"}).status_code == 200


# -- Compresión ------------------------------------------------------------------------------


def _compressing_gateway() -> ApiGateway:
    return ApiGateway(
        compression=CompressionNegotiator(
            [GzipCompressionProvider()], policy=CompressionPolicy(minimum_size_bytes=100)
        )
    )


def test_a_large_response_is_gzipped_when_the_client_accepts_it() -> None:
    app = _routed_app()
    _compressing_gateway().install(app)

    response = TestClient(app).get("/api/v1/items", headers={"Accept-Encoding": "gzip"})
    assert response.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["Vary"]
    # ``httpx`` descomprime solo; el contenido debe seguir siendo el original.
    assert len(response.json()["items"]) == 80


def test_a_client_that_does_not_accept_gzip_gets_plain_bytes() -> None:
    app = _routed_app()
    _compressing_gateway().install(app)

    response = TestClient(app).get("/api/v1/items", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in response.headers
    assert len(response.json()["items"]) == 80


def test_a_small_response_is_not_compressed() -> None:
    app = _routed_app()
    _compressing_gateway().install(app)

    response = TestClient(app).get("/ping", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in response.headers


def test_the_response_really_travels_smaller_over_the_wire() -> None:
    """``TestClient`` descomprime de forma transparente, así que los bytes
    comprimidos no se ven en ``response.content``. Lo que sí se ve es
    ``Content-Length``, que el middleware recalcula sobre el cuerpo ya
    comprimido: comparar ese valor con el tamaño real descomprimido demuestra
    que la compresión ocurrió de verdad y no solo se anunció."""
    app = _routed_app()
    _compressing_gateway().install(app)

    response = TestClient(app).get("/api/v1/items", headers={"Accept-Encoding": "gzip"})
    compressed_length = int(response.headers["Content-Length"])
    original_length = len(json.dumps(response.json(), separators=(",", ":")).encode())

    assert response.headers["Content-Encoding"] == "gzip"
    assert compressed_length < original_length


# -- Idempotencia -------------------------------------------------------------------------------


def test_a_retry_with_the_same_key_and_body_replays_the_original_response() -> None:
    app = _routed_app()
    ApiGateway(idempotency=IdempotencyManager()).install(app)
    client = TestClient(app)

    first = client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})
    second = client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})

    assert first.json() == second.json() == {"sequence": 1}
    assert second.headers["X-Idempotent-Replay"] == "true"


def test_reusing_a_key_with_a_different_body_gets_409() -> None:
    app = _routed_app()
    ApiGateway(idempotency=IdempotencyManager()).install(app)
    client = TestClient(app)

    client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})
    conflict = client.post("/api/v1/orders", json={"sku": "B"}, headers={"Idempotency-Key": "k1"})

    assert conflict.status_code == 409
    assert conflict.json()["type"] == "https://teaf.torus/errors/idempotency-conflict"


def test_different_keys_execute_the_endpoint_each_time() -> None:
    app = _routed_app()
    ApiGateway(idempotency=IdempotencyManager()).install(app)
    client = TestClient(app)

    first = client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})
    second = client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k2"})
    assert first.json()["sequence"] != second.json()["sequence"]


def test_a_request_without_an_idempotency_key_is_never_deduplicated() -> None:
    app = _routed_app()
    ApiGateway(idempotency=IdempotencyManager()).install(app)
    client = TestClient(app)

    first = client.post("/api/v1/orders", json={"sku": "A"})
    second = client.post("/api/v1/orders", json={"sku": "A"})
    assert first.json()["sequence"] != second.json()["sequence"]


def test_the_endpoint_can_still_read_its_body_behind_the_middleware() -> None:
    """El middleware consume el cuerpo para calcular la huella y debe reponerlo,
    o todo endpoint con payload recibiría un cuerpo vacío."""
    app = FastAPI()

    @app.post("/echo")
    async def echo(payload: dict[str, str]) -> dict[str, str]:
        return payload

    ApiGateway(idempotency=IdempotencyManager()).install(app)

    response = TestClient(app).post(
        "/echo", json={"hola": "mundo"}, headers={"Idempotency-Key": "k1"}
    )
    assert response.json() == {"hola": "mundo"}


# -- Auditoría -----------------------------------------------------------------------------------


def test_every_served_request_is_audited() -> None:
    app = _routed_app()
    sink = InMemoryAuditSink()
    ApiGateway(audit=ApiAudit([sink])).install(app)
    client = TestClient(app)

    client.get("/ping")
    client.post("/api/v1/orders", json={"sku": "A"})

    assert [(r.method, r.path, r.status_code) for r in sink.records] == [
        ("GET", "/ping", 200),
        ("POST", "/api/v1/orders", 200),
    ]
    assert all(record.latency_seconds > 0 for record in sink.records)


def test_rejected_requests_are_audited_too() -> None:
    """Una auditoría que solo viera el tráfico aceptado sería inútil para lo
    que más importa auditar."""
    app = _routed_app()
    sink = InMemoryAuditSink()
    ApiGateway(
        audit=ApiAudit([sink]),
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=1, window_seconds=60)]),
    ).install(app)
    client = TestClient(app)

    client.get("/ping")
    client.get("/ping")

    assert [record.outcome.value for record in sink.records] == ["accepted", "rejected"]
    assert sink.records[-1].status_code == 429


def test_a_failing_endpoint_is_audited_as_failed() -> None:
    app = _routed_app()
    sink = InMemoryAuditSink()
    ApiGateway(audit=ApiAudit([sink])).install(app)

    client = TestClient(app, raise_server_exceptions=False)
    client.get("/boom")

    assert sink.records[-1].outcome.value == "failed"
    assert sink.records[-1].status_code == 500


def test_a_replayed_response_is_audited_as_such() -> None:
    app = _routed_app()
    sink = InMemoryAuditSink()
    ApiGateway(audit=ApiAudit([sink]), idempotency=IdempotencyManager()).install(app)
    client = TestClient(app)

    client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})
    client.post("/api/v1/orders", json={"sku": "A"}, headers={"Idempotency-Key": "k1"})

    assert [record.outcome.value for record in sink.records] == ["accepted", "replayed"]


def test_the_audit_record_carries_the_negotiated_api_version() -> None:
    app = _routed_app()
    sink = InMemoryAuditSink()
    ApiGateway(
        audit=ApiAudit([sink]),
        versioning=ApiVersionNegotiator(
            ApiVersioningPolicy(supported=(ApiVersion(1), ApiVersion(2)), default=ApiVersion(1))
        ),
    ).install(app)

    TestClient(app).get("/ping", headers={"X-API-Version": "2"})
    assert sink.records[-1].api_version == "v2"


# -- Convivencia con el resto del framework ------------------------------------------------------


def test_the_platform_coexists_with_the_frameworks_own_middlewares() -> None:
    """Instalado sobre ``Application``, el gateway queda por fuera de
    ``RequestIdMiddleware`` — el correlation-id debe seguir llegando a la
    auditoría a través de la cabecera entrante."""
    sink = InMemoryAuditSink()
    application = Application(settings=TestingSettings())
    ApiGateway(audit=ApiAudit([sink])).install(application.asgi)

    with TestClient(application.asgi) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "corr-abc"})

    assert response.status_code == 200
    assert sink.records[-1].correlation_id == "corr-abc"


def test_the_module_protects_a_real_application_end_to_end() -> None:
    module = ApiProtectionModule(
        ApiProtectionConfiguration(
            rate_limit_requests=2,
            rate_limit_window_seconds=60.0,
            cors_allow_origins=(_ORIGIN,),
            idempotency_enabled=True,
        )
    )
    application = Application(settings=TestingSettings(), modules=[module])
    module.gateway.install(application.asgi)

    with TestClient(application.asgi) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        limited = client.get("/health")

    assert limited.status_code == 429
    # La auditoría del propio módulo registró las tres.
    assert len(module.audit_sink.records) == 3


def test_the_platform_events_reach_the_runtime_event_bus() -> None:
    module = ApiProtectionModule(
        ApiProtectionConfiguration(rate_limit_requests=1, rate_limit_window_seconds=60.0)
    )
    application = Application(settings=TestingSettings(), modules=[module])
    module.gateway.install(application.asgi)

    seen: list[Event] = []
    with TestClient(application.asgi) as client:
        for name in ("request.accepted", "request.rejected", "rate.limit.exceeded"):
            application.runtime.event_bus.subscribe(name, seen.append)
        client.get("/health")
        client.get("/health")

    published = {event.name for event in seen}
    assert "request.accepted" in published
    assert "rate.limit.exceeded" in published
    assert "request.rejected" in published


@pytest.mark.parametrize("path", ["/health", "/live", "/ready", "/info"])
def test_the_frameworks_own_routes_keep_working_behind_the_platform(path: str) -> None:
    module = ApiProtectionModule()
    application = Application(settings=TestingSettings(), modules=[module])
    module.gateway.install(application.asgi)

    with TestClient(application.asgi) as client:
        assert client.get(path).status_code == 200
