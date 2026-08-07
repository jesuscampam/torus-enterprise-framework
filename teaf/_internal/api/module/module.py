"""``ApiProtectionModule`` — el módulo oficial de protección de APIs, sobre el Module SDK.

Mismo patrón que ``DatabaseModule``/``SecurityModule``/``ObservabilityModule``:
todo lo concreto (limitador, gestor de cuotas, política CORS, negociador de
versiones, validador, negociador de compresión, gestor de idempotencia,
auditoría y el propio ``ApiGateway``) se construye en ``__init__`` — no en
``initialize()`` — porque ``ModuleBase.bootstrap()`` llama a
``get_manifest()`` **antes** de ejecutar cualquier hook del ciclo de vida, y
el manifiesto necesita esas instancias ya construidas para declarar sus
servicios.

``gateway`` queda disponible como atributo público inmediatamente después de
construir el módulo —**antes** de pasarlo a ``Application(modules=[...])``—
porque ``gateway.install(app)`` debe ejecutarse antes de que arranque el
ciclo de vida ASGI, igual que ``SecurityMiddleware`` con
``provider_registry``/``principal_resolver`` (ver ``modules/security/module.py``).

Ubicación: este módulo vive junto a su subsistema (``teaf/_internal/api/module/``)
en lugar de en ``teaf/_internal/modules/``, siguiendo la estructura fijada
por el Sprint 2.9 para ``teaf._internal.api``. El *patrón* es idéntico al de
los otros tres módulos —``configuration.py`` + ``health.py`` + ``manifest.py``
+ ``module.py``, con ``ModuleBase`` y ``ModuleBuilder``—; solo cambia dónde
se guardan los cuatro archivos (ver ADR-009).
"""

from __future__ import annotations

from collections.abc import Sequence

from teaf._internal.api.audit.audit import ApiAudit
from teaf._internal.api.compression.providers import (
    BrotliCompressionProvider,
    CompressionNegotiator,
    CompressionPolicy,
    GzipCompressionProvider,
)
from teaf._internal.api.cors.policy import CorsPolicy
from teaf._internal.api.gateway.gateway import ApiGateway
from teaf._internal.api.idempotency.manager import IdempotencyManager
from teaf._internal.api.models import QuotaRule, RateLimitRule
from teaf._internal.api.module.configuration import (
    ApiProtectionConfiguration,
    build_quota_rules,
    build_rate_limit_rules,
)
from teaf._internal.api.module.health import ApiProtectionHealth
from teaf._internal.api.module.manifest import build_api_protection_manifest
from teaf._internal.api.providers.memory import (
    InMemoryAuditSink,
    InMemoryRateLimitStore,
    LoggingAuditSink,
)
from teaf._internal.api.providers.redis import RedisRateLimitStore
from teaf._internal.api.quotas.manager import QuotaManager
from teaf._internal.api.ratelimit.limiter import RateLimiter
from teaf._internal.api.validation.validator import RequestValidationPolicy, RequestValidator
from teaf._internal.api.versioning.negotiator import ApiVersioningPolicy, ApiVersionNegotiator
from teaf._internal.contracts.api import AuditSink, CompressionProvider
from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.contracts.telemetry import Meter
from teaf._internal.runtime.event_bus import Event
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


class ApiProtectionModule(ModuleBase):
    """Plataforma de protección de APIs: limitación, cuotas, CORS, versionado,
    validación, compresión, idempotencia y auditoría."""

    def __init__(
        self,
        configuration: ApiProtectionConfiguration | None = None,
        *,
        rate_limit_rules: Sequence[RateLimitRule] | None = None,
        quota_rules: Sequence[QuotaRule] | None = None,
        audit_sinks: Sequence[AuditSink] = (),
        compression_providers: Sequence[CompressionProvider] | None = None,
        cache_provider: CacheProvider | None = None,
        meter: Meter | None = None,
    ) -> None:
        """Los argumentos por palabra clave son la vía para lo que no cabe en
        configuración escalar: varias reglas de limitación o de cuota, un
        destino de auditoría propio (una tabla, un SIEM), un proveedor de
        compresión distinto, o el ``Meter`` de ``ObservabilityModule`` para
        que la auditoría emita también métricas.

        Cuando ``rate_limit_rules``/``quota_rules`` son ``None`` se derivan de
        la configuración escalar (``build_rate_limit_rules``/
        ``build_quota_rules``); pasar una secuencia vacía desactiva ese
        subsistema explícitamente.
        """
        super().__init__()
        self.configuration = configuration or ApiProtectionConfiguration()
        config = self.configuration

        rules = (
            build_rate_limit_rules(config) if rate_limit_rules is None else tuple(rate_limit_rules)
        )
        # Con ``cache_provider`` los tres almacenes pasan a ser distribuidos y
        # el estado se comparte entre réplicas; sin él siguen siendo por
        # proceso, que es el comportamiento de siempre. Es el único punto del
        # subsistema donde se elige, y no cambia ninguna firma: ADR-009 diseñó
        # los contratos precisamente para que esto no requiriera rediseño.
        self.cache_provider = cache_provider
        self.rate_limit_store = (
            RedisRateLimitStore(cache_provider)
            if cache_provider is not None
            else InMemoryRateLimitStore()
        )
        self.rate_limiter = RateLimiter(
            rules, store=self.rate_limit_store, enabled=config.rate_limit_enabled
        )

        quotas = build_quota_rules(config) if quota_rules is None else tuple(quota_rules)
        self.quota_manager = QuotaManager(quotas, enabled=config.quotas_enabled)

        self.cors = CorsPolicy(
            allow_origins=config.cors_allow_origins,
            allow_origin_patterns=config.cors_allow_origin_patterns,
            allow_methods=config.cors_allow_methods,
            allow_headers=config.cors_allow_headers,
            expose_headers=config.cors_expose_headers,
            allow_credentials=config.cors_allow_credentials,
            max_age_seconds=config.cors_max_age_seconds,
        )

        self.versioning = ApiVersionNegotiator(
            ApiVersioningPolicy(
                supported=config.supported_versions,
                default=config.default_version,
                strategies=config.versioning_strategy_enums,
                header_name=config.versioning_header,
                media_type_vendor=config.versioning_media_type_vendor,
                strict=config.versioning_strict,
            )
        )

        self.validator = RequestValidator(
            RequestValidationPolicy(
                max_request_bytes=config.validation_max_request_bytes,
                max_response_bytes=config.validation_max_response_bytes,
                allowed_content_types=config.validation_allowed_content_types,
                required_headers=config.validation_required_headers,
                blocked_user_agents=config.validation_blocked_user_agents,
                allowed_user_agents=config.validation_allowed_user_agents,
                require_user_agent=config.validation_require_user_agent,
                max_url_length=config.validation_max_url_length,
            )
        )

        self.compression = CompressionNegotiator(
            self._build_compression_providers(config, compression_providers),
            policy=CompressionPolicy(
                enabled=config.compression_enabled,
                minimum_size_bytes=config.compression_minimum_size_bytes,
            ),
        )

        self.idempotency = IdempotencyManager(
            ttl_seconds=config.idempotency_ttl_seconds,
            methods=config.idempotency_methods,
            header_name=config.idempotency_header,
            enabled=config.idempotency_enabled,
        )

        self.audit_sink = InMemoryAuditSink(limit=config.audit_memory_sink_limit)
        self.audit = ApiAudit(
            self._build_audit_sinks(config, audit_sinks),
            meter=meter,
            enabled=config.audit_enabled,
        )

        self.gateway = ApiGateway(
            rate_limiter=self.rate_limiter if config.rate_limit_enabled else None,
            quota_manager=self.quota_manager if config.quotas_enabled else None,
            cors=self.cors if self.cors.enabled else None,
            versioning=self.versioning if config.versioning_enabled else None,
            validator=self.validator if config.validation_enabled else None,
            compression=self.compression if config.compression_enabled else None,
            idempotency=self.idempotency if config.idempotency_enabled else None,
            audit=self.audit if config.audit_enabled else None,
            trust_forwarded_headers=config.trust_forwarded_headers,
            trusted_proxies=config.trusted_proxies,
            validate_responses=config.validation_validate_responses,
        )

        self.health = ApiProtectionHealth(self.gateway)

    def _build_compression_providers(
        self,
        config: ApiProtectionConfiguration,
        overrides: Sequence[CompressionProvider] | None,
    ) -> tuple[CompressionProvider, ...]:
        """Proveedores de compresión, en orden de preferencia del servidor.

        Brotli va primero cuando está disponible: comprime mejor que GZip, y
        si el cliente no lo admite el negociador cae a GZip solo (la
        preferencia del cliente manda, ver ``CompressionNegotiator.select``).
        """
        if overrides is not None:
            return tuple(overrides)
        providers: list[CompressionProvider] = []
        if config.compression_brotli_enabled:
            providers.append(BrotliCompressionProvider(quality=config.compression_brotli_quality))
        if config.compression_gzip_enabled:
            providers.append(GzipCompressionProvider(level=config.compression_gzip_level))
        return tuple(providers)

    def _build_audit_sinks(
        self, config: ApiProtectionConfiguration, extra: Sequence[AuditSink]
    ) -> tuple[AuditSink, ...]:
        sinks: list[AuditSink] = []
        if config.audit_memory_sink_enabled:
            sinks.append(self.audit_sink)
        if config.audit_logging_sink_enabled:
            sinks.append(LoggingAuditSink())
        sinks.extend(extra)
        return tuple(sinks)

    def get_manifest(self) -> ModuleManifest:
        return build_api_protection_manifest(
            self.configuration, gateway=self.gateway, health=self.health
        )

    async def configure(self, context: ModuleContext) -> None:
        """Conecta el ``EventBus`` del Runtime al gateway y a la auditoría.

        Se hace aquí y no en ``__init__`` porque el ``EventBus`` pertenece al
        ``Runtime``, que solo está disponible a través del ``ModuleContext``.
        El gateway conserva la referencia para pasársela a cada middleware
        que instale después.
        """
        self.gateway.event_bus = context.runtime.event_bus
        self.audit.event_bus = context.runtime.event_bus

    async def start(self, context: ModuleContext) -> None:
        """Refresca la caché de salud — sin I/O que abrir (todo es en memoria)."""
        status = await self.health.refresh()
        context.runtime.event_bus.publish(
            Event(
                name="health.changed",
                payload={"module": "api-protection", "status": status.value},
            )
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info(
            "api_protection_module_ready",
            extra={"context": self.gateway.describe()},
        )

    async def stop(self, context: ModuleContext) -> None:
        """Libera el estado de limitación ya expirado antes de apagar.

        La expiración del almacén en memoria es perezosa (solo limpia lo que
        se consulta), así que un barrido explícito al apagar evita arrastrar
        claves muertas si el proceso se reinicia en caliente.
        """
        # Solo el almacén en memoria necesita el barrido: en Redis la
        # expiración la lleva el propio servidor con el TTL de cada clave.
        if isinstance(self.rate_limit_store, InMemoryRateLimitStore):
            self.rate_limit_store.purge_expired()
