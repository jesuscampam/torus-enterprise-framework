"""Pruebas unitarias de ``ApiGateway``, ``ApiProtectionModule`` y su configuración.

Cubre el orden de la cadena de middlewares, la evaluación fuera de HTTP
(``evaluate()``), el registro automático en el contenedor de dependencias, y
la derivación de reglas desde configuración escalar (Sprint 2.9, ADR-009).
"""

from __future__ import annotations

import asyncio

import pytest
from teaf import Application
from teaf._internal.api.module.configuration import build_quota_rules, build_rate_limit_rules
from teaf._internal.api.module.manifest import API_PROTECTION_EVENTS
from teaf._internal.contracts.api import CompressionProvider
from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.providers.cache.memory import InMemoryCacheProvider
from teaf.api import (
    MIDDLEWARE_ORDER,
    ApiAudit,
    ApiGateway,
    ApiProtectionConfiguration,
    ApiProtectionModule,
    ApiRequestContext,
    ApiVersion,
    CorsPolicy,
    IdempotencyManager,
    ProtectionScope,
    QuotaKind,
    QuotaManager,
    QuotaPeriod,
    QuotaRule,
    RateLimitAlgorithm,
    RateLimiter,
    RateLimitRule,
    RedisIdempotencyStore,
    RedisQuotaStore,
    RedisRateLimitStore,
    RequestValidator,
)

# -- Gateway: composición ------------------------------------------------------------


def test_an_empty_gateway_installs_nothing() -> None:
    assert ApiGateway().enabled_middlewares == ()


def test_only_configured_subsystems_produce_middlewares() -> None:
    gateway = ApiGateway(rate_limiter=RateLimiter(), audit=ApiAudit())
    assert gateway.enabled_middlewares == ("audit", "rate_limit")


def test_cors_without_origins_installs_no_middleware() -> None:
    """Una política CORS vacía no protege nada — montar su middleware sería
    coste puro."""
    assert ApiGateway(cors=CorsPolicy()).enabled_middlewares == ()
    assert ApiGateway(cors=CorsPolicy(allow_origins=("*",))).enabled_middlewares == ("cors",)


def test_middlewares_are_reported_in_execution_order() -> None:
    gateway = ApiGateway(
        rate_limiter=RateLimiter(),
        quota_manager=QuotaManager(),
        cors=CorsPolicy(allow_origins=("*",)),
        validator=RequestValidator(),
        idempotency=IdempotencyManager(),
        audit=ApiAudit(),
    )
    installed = gateway.enabled_middlewares
    assert list(installed) == [name for name in MIDDLEWARE_ORDER if name in installed]
    # CORS el más externo, idempotencia el más interno — ver MIDDLEWARE_ORDER.
    assert installed[0] == "cors"
    assert installed[-1] == "idempotency"


def test_install_registers_middlewares_from_innermost_to_outermost() -> None:
    """Starlette ejecuta los middlewares en orden inverso al de registro, así
    que ``install()`` debe recorrer la cadena al revés."""

    class _FakeApp:
        def __init__(self) -> None:
            self.registered: list[str] = []

        def add_middleware(self, middleware_class: type, **options: object) -> None:
            self.registered.append(middleware_class.__name__)

    app = _FakeApp()
    gateway = ApiGateway(
        cors=CorsPolicy(allow_origins=("*",)), audit=ApiAudit(), rate_limiter=RateLimiter()
    )
    installed = gateway.install(app)

    assert installed == ("cors", "audit", "rate_limit")
    assert app.registered == ["RateLimitMiddleware", "ApiAuditMiddleware", "CorsMiddleware"]


def test_install_rejects_an_application_without_add_middleware() -> None:
    with pytest.raises(AttributeError):
        ApiGateway(audit=ApiAudit()).install(object())  # type: ignore[arg-type]


def test_describe_summarises_the_configured_protection() -> None:
    gateway = ApiGateway(
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=1, window_seconds=60)]),
        quota_manager=QuotaManager([QuotaRule(name="daily", limit=10)]),
        cors=CorsPolicy(allow_origins=("*",)),
    )
    described = gateway.describe()
    assert described["rateLimitRules"] == ["ip"]
    assert described["quotaRules"] == ["daily"]
    assert described["corsEnabled"] is True
    assert described["idempotencyEnabled"] is False


# -- Gateway: evaluación fuera de HTTP -------------------------------------------------


def test_evaluate_accepts_while_there_is_room() -> None:
    async def scenario() -> None:
        gateway = ApiGateway(
            rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=2, window_seconds=60)])
        )
        context = ApiRequestContext(client_ip="1.1.1.1")

        assert (await gateway.evaluate(context)).allowed is True
        assert (await gateway.evaluate(context)).allowed is True

        decision = await gateway.evaluate(context)
        assert decision.allowed is False
        assert decision.reason == "rate-limit-exceeded"
        assert decision.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in decision.headers

    asyncio.run(scenario())


def test_evaluate_reports_an_exhausted_quota() -> None:
    async def scenario() -> None:
        gateway = ApiGateway(
            quota_manager=QuotaManager(
                [QuotaRule(name="daily", limit=1, scope=ProtectionScope.TENANT)]
            )
        )
        context = ApiRequestContext(tenant_id="acme")

        assert (await gateway.evaluate(context)).allowed is True
        decision = await gateway.evaluate(context)
        assert decision.allowed is False
        assert decision.reason == "quota-exceeded"
        assert decision.quota is not None
        assert decision.headers["X-Quota-Remaining"] == "0"

    asyncio.run(scenario())


def test_rate_limiting_is_evaluated_before_quotas() -> None:
    """No tiene sentido gastar cuota contratada en una petición que va a
    rechazarse igualmente por límite de caudal."""

    async def scenario() -> None:
        quotas = QuotaManager([QuotaRule(name="daily", limit=100, scope=ProtectionScope.TENANT)])
        gateway = ApiGateway(
            rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=1, window_seconds=60)]),
            quota_manager=quotas,
        )
        context = ApiRequestContext(client_ip="1.1.1.1", tenant_id="acme")

        await gateway.evaluate(context)
        decision = await gateway.evaluate(context)
        assert decision.reason == "rate-limit-exceeded"

        usage = await quotas.usage(context)
        assert usage[0].consumed == pytest.approx(1.0)

    asyncio.run(scenario())


def test_release_frees_the_concurrency_quota_taken_by_evaluate() -> None:
    async def scenario() -> None:
        gateway = ApiGateway(
            quota_manager=QuotaManager([QuotaRule(name="conc", kind=QuotaKind.CONCURRENT, limit=1)])
        )
        context = ApiRequestContext(tenant_id="acme")

        assert (await gateway.evaluate(context)).allowed is True
        assert (await gateway.evaluate(context)).allowed is False

        await gateway.release(context)
        assert (await gateway.evaluate(context)).allowed is True

    asyncio.run(scenario())


def test_an_empty_gateway_allows_everything() -> None:
    async def scenario() -> None:
        assert (await ApiGateway().evaluate(ApiRequestContext())).allowed is True

    asyncio.run(scenario())


def test_a_gateway_decision_is_serialisable() -> None:
    async def scenario() -> None:
        gateway = ApiGateway(
            rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=1, window_seconds=60)])
        )
        context = ApiRequestContext(client_ip="1.1.1.1")
        await gateway.evaluate(context)
        payload = (await gateway.evaluate(context)).as_dict()

        assert payload["allowed"] is False
        assert payload["reason"] == "rate-limit-exceeded"
        assert payload["rateLimit"] is not None

    asyncio.run(scenario())


# -- Configuración: derivación de reglas -----------------------------------------------


def test_rate_limit_rules_derive_from_scalar_configuration() -> None:
    configuration = ApiProtectionConfiguration(
        rate_limit_requests=50,
        rate_limit_window_seconds=30.0,
        rate_limit_algorithm="token_bucket",
        rate_limit_scope="tenant",
        rate_limit_burst=75,
    )
    (rule,) = build_rate_limit_rules(configuration)
    assert rule.limit == 50
    assert rule.algorithm is RateLimitAlgorithm.TOKEN_BUCKET
    assert rule.scope is ProtectionScope.TENANT
    assert rule.capacity == 75


def test_no_rate_limit_rule_is_built_when_it_is_disabled() -> None:
    assert build_rate_limit_rules(ApiProtectionConfiguration(rate_limit_enabled=False)) == ()
    assert build_rate_limit_rules(ApiProtectionConfiguration(rate_limit_requests=0)) == ()


def test_only_quotas_with_a_positive_limit_are_built() -> None:
    configuration = ApiProtectionConfiguration(
        quotas_enabled=True,
        quota_requests_per_day=1_000,
        quota_max_concurrent_requests=5,
    )
    rules = build_quota_rules(configuration)
    assert {rule.name for rule in rules} == {"requests-per-day", "max-concurrent"}
    by_name = {rule.name: rule for rule in rules}
    assert by_name["requests-per-day"].period is QuotaPeriod.DAY
    assert by_name["max-concurrent"].kind is QuotaKind.CONCURRENT


def test_no_quotas_are_built_when_they_are_disabled() -> None:
    assert build_quota_rules(ApiProtectionConfiguration(quota_requests_per_day=10)) == ()


def test_an_unrecognised_enum_value_falls_back_to_a_safe_default() -> None:
    configuration = ApiProtectionConfiguration(
        rate_limit_algorithm="quantum_window", rate_limit_scope="galaxy", quota_scope="galaxy"
    )
    assert configuration.algorithm is RateLimitAlgorithm.FIXED_WINDOW
    assert configuration.scope is ProtectionScope.IP
    assert configuration.quota_protection_scope is ProtectionScope.TENANT


# -- Configuración: from_mapping --------------------------------------------------------


def test_from_mapping_accepts_both_bare_and_prefixed_keys() -> None:
    prefixed = ApiProtectionConfiguration.from_mapping({"api_rate_limit_requests": 7})
    bare = ApiProtectionConfiguration.from_mapping({"rate_limit_requests": 7})
    assert prefixed.rate_limit_requests == bare.rate_limit_requests == 7


def test_from_mapping_parses_comma_separated_lists() -> None:
    """Una variable de entorno solo sabe de cadenas."""
    configuration = ApiProtectionConfiguration.from_mapping(
        {"api_cors_allow_origins": "https://a.com, https://b.com"}
    )
    assert configuration.cors_allow_origins == ("https://a.com", "https://b.com")


def test_from_mapping_also_accepts_already_typed_sequences() -> None:
    configuration = ApiProtectionConfiguration.from_mapping(
        {"api_cors_allow_origins": ["https://a.com"]}
    )
    assert configuration.cors_allow_origins == ("https://a.com",)


@pytest.mark.parametrize("raw", ["true", "1", "yes", "on", True])
def test_from_mapping_coerces_truthy_booleans(raw: object) -> None:
    assert ApiProtectionConfiguration.from_mapping({"api_quotas_enabled": raw}).quotas_enabled


@pytest.mark.parametrize("raw", ["false", "0", "no", "off", False])
def test_from_mapping_coerces_falsy_booleans(raw: object) -> None:
    assert not ApiProtectionConfiguration.from_mapping({"api_quotas_enabled": raw}).quotas_enabled


def test_from_mapping_on_an_empty_mapping_yields_the_defaults() -> None:
    assert ApiProtectionConfiguration.from_mapping({}) == ApiProtectionConfiguration()


def test_the_settings_of_the_framework_feed_the_configuration_directly() -> None:
    """``from_mapping(settings.model_dump())`` debe funcionar sin transformar nada."""
    from teaf._internal.config.settings import TestingSettings

    configuration = ApiProtectionConfiguration.from_mapping(TestingSettings().model_dump())
    assert configuration.rate_limit_requests == 1_000
    assert configuration.versioning_supported == ("v1",)


def test_supported_versions_discard_unparseable_entries() -> None:
    configuration = ApiProtectionConfiguration(versioning_supported=("v1", "banana", "v2"))
    assert configuration.supported_versions == (ApiVersion(1), ApiVersion(2))


def test_supported_versions_never_end_up_empty() -> None:
    configuration = ApiProtectionConfiguration(versioning_supported=("banana",))
    assert configuration.supported_versions == (ApiVersion(1),)


# -- Módulo -------------------------------------------------------------------------------


def test_the_module_builds_its_gateway_before_bootstrap() -> None:
    """``gateway.install(app)`` debe poder llamarse antes de arrancar el ciclo
    de vida ASGI, así que el gateway existe ya tras construir el módulo."""
    module = ApiProtectionModule()
    assert module.gateway.enabled_middlewares != ()


def test_the_manifest_declares_the_eight_platform_events() -> None:
    manifest = ApiProtectionModule().get_manifest()
    assert set(manifest.events) == set(API_PROTECTION_EVENTS)
    assert len(API_PROTECTION_EVENTS) == 8


def test_the_manifest_declares_a_capability_per_subsystem() -> None:
    manifest = ApiProtectionModule().get_manifest()
    ids = {capability.id for capability in manifest.capabilities}
    assert ids == {
        "api.protection",
        "api.rate-limit",
        "api.quota",
        "api.cors",
        "api.versioning",
        "api.validation",
        "api.compression",
        "api.idempotency",
        "api.audit",
    }


def test_only_the_services_of_configured_subsystems_are_declared() -> None:
    """Registrar un ``QuotaManager`` inexistente haría que resolverlo
    devolviera algo inservible en vez de fallar claramente."""
    default_contracts = {
        service.contract for service in ApiProtectionModule().get_manifest().services
    }
    assert QuotaManager not in default_contracts
    assert RateLimiter in default_contracts

    with_quotas = ApiProtectionModule(
        ApiProtectionConfiguration(quotas_enabled=True, quota_requests_per_day=10)
    )
    assert QuotaManager in {s.contract for s in with_quotas.get_manifest().services}


def test_the_module_registers_its_services_in_the_container() -> None:
    async def scenario() -> None:
        module = ApiProtectionModule(
            ApiProtectionConfiguration(
                quotas_enabled=True, quota_requests_per_day=10, idempotency_enabled=True
            )
        )
        application = Application(modules=[module])
        async with application.asgi.router.lifespan_context(application.asgi):
            runtime = application.runtime
            assert runtime.resolve_service(ApiGateway) is module.gateway
            assert runtime.resolve_service(RateLimiter) is module.rate_limiter
            assert runtime.resolve_service(QuotaManager) is module.quota_manager
            assert runtime.resolve_service(ApiAudit) is module.audit
            assert runtime.resolve_service(RequestValidator) is module.validator
            assert runtime.resolve_service(IdempotencyManager) is module.idempotency
            assert runtime.resolve_service(CompressionProvider) is not None

    asyncio.run(scenario())


def test_the_module_connects_the_event_bus_during_bootstrap() -> None:
    async def scenario() -> None:
        module = ApiProtectionModule()
        application = Application(modules=[module])
        async with application.asgi.router.lifespan_context(application.asgi):
            assert module.gateway.event_bus is application.runtime.event_bus
            assert module.audit.event_bus is application.runtime.event_bus

    asyncio.run(scenario())


def test_the_module_reports_healthy_when_something_is_protected() -> None:
    async def scenario() -> None:
        module = ApiProtectionModule()
        application = Application(modules=[module])
        async with application.asgi.router.lifespan_context(application.asgi):
            assert module.health.check().value == "healthy"

    asyncio.run(scenario())


def test_the_module_reports_degraded_when_nothing_is_protected() -> None:
    """Sin nada que aplicar no está rota, pero tampoco protege — y eso el
    operador debe verlo en /health, no descubrirlo en un incidente."""

    async def scenario() -> None:
        module = ApiProtectionModule(
            ApiProtectionConfiguration(
                rate_limit_enabled=False,
                versioning_enabled=False,
                validation_enabled=False,
                compression_enabled=False,
                audit_enabled=False,
            )
        )
        assert module.gateway.enabled_middlewares == ()
        assert await module.health.refresh() is not None
        assert module.health.check().value == "degraded"

    asyncio.run(scenario())


def test_explicit_rules_override_the_scalar_configuration() -> None:
    module = ApiProtectionModule(
        rate_limit_rules=[RateLimitRule(name="custom", limit=5, window_seconds=1.0)]
    )
    assert [rule.name for rule in module.rate_limiter.rules] == ["custom"]


def test_an_empty_rule_sequence_disables_the_subsystem_explicitly() -> None:
    module = ApiProtectionModule(rate_limit_rules=[])
    assert module.rate_limiter.rules == ()


# -- Proveedores preparados de Redis -------------------------------------------------------


@pytest.mark.parametrize(
    "provider_class", [RedisRateLimitStore, RedisQuotaStore, RedisIdempotencyStore]
)
def test_the_redis_providers_are_implemented_over_the_cache_contract(
    provider_class: type,
) -> None:
    """Sprint 3.0 los implementa: hasta 2.9.2 lanzaban ``NotImplementedError``.

    Lo que se fija aquí es la frontera: cada almacén se construye sobre un
    ``CacheProvider`` —no sobre un cliente de Redis propio—, de modo que el
    ciclo de vida de la conexión vive en un solo sitio (el módulo de caché) y
    estos objetos no abren ninguna. La lógica de cada uno se prueba en
    ``tests/unit/test_cache_module.py``.
    """
    store = provider_class(InMemoryCacheProvider())
    assert isinstance(store.provider, CacheProvider)


@pytest.mark.parametrize(
    "provider_class", [RedisRateLimitStore, RedisQuotaStore, RedisIdempotencyStore]
)
def test_the_redis_providers_require_a_cache_provider(provider_class: type) -> None:
    """Sin proveedor no hay almacén: construirlos "por si acaso" no debe colar."""
    with pytest.raises(TypeError):
        provider_class()
