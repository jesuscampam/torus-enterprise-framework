"""Pruebas unitarias de teaf/__init__.py — la superficie pública completa."""

from __future__ import annotations

import teaf

_EXPECTED_ALL = {
    "Application",
    "Runtime",
    "Module",
    "ModuleBase",
    "ModuleBuilder",
    "ModuleContext",
    "ModuleManifest",
    "ServiceContainer",
    "EventBus",
    "CapabilityRegistry",
    "ModuleRegistry",
    "Health",
    "Configuration",
    "Version",
    "CapabilityCategory",
    "Event",
    "Lifetime",
    "ModuleCategory",
    "get_configuration",
    # -- Plataforma de seguridad empresarial (Sprint 2.7, ADR-007).
    "ANONYMOUS_IDENTITY",
    "ANONYMOUS_PRINCIPAL",
    "AnonymousIdentityProvider",
    "ApiKeyIdentityProvider",
    "ApiKeyProvider",
    "ApiKeyRecord",
    "ApiKeyStore",
    "Argon2PasswordHasher",
    "AuthenticationCredentials",
    "AuthenticationProvider",
    "AuthenticationResult",
    "AuthorizationProvider",
    "AzureADProvider",
    "BcryptPasswordHasher",
    "Claims",
    "CryptoProvider",
    "DefaultPolicyEvaluator",
    "HmacCryptoProvider",
    "Identity",
    "IdentityProvider",
    "IdentityProviderRegistry",
    "InMemoryApiKeyStore",
    "InMemoryTokenRevocationStore",
    "JWTIdentityProvider",
    "JWTProvider",
    "LDAPProvider",
    "OAuth2IdentityProvider",
    "OpenIDConnectProvider",
    "PasswordHasher",
    "Permission",
    "PermissionResolver",
    "Policy",
    "PolicyEvaluator",
    "PolicyRule",
    "Principal",
    "PrincipalResolver",
    "Role",
    "RolePermissionResolver",
    "RoleResolver",
    "SAMLIdentityProvider",
    "SecurityContext",
    "SecurityMiddleware",
    "StaticRoleResolver",
    "TokenPair",
    "TokenProvider",
    "TokenRevocationStore",
    "allow_anonymous",
    "authorize",
    "current_claims",
    "current_identity",
    "current_principal",
    "current_security_context",
    # -- Plataforma de observabilidad empresarial (Sprint 2.8, ADR-008).
    "AzureMonitorExporter",
    "CompositeHealthChecker",
    "ConsoleExporter",
    "Counter",
    "DatadogExporter",
    "DiagnosticReport",
    "DynatraceExporter",
    "ElasticExporter",
    "Exporter",
    "Gauge",
    "GrafanaExporter",
    "HealthCheck",
    "HealthReport",
    "HealthStatus",
    "Histogram",
    "JaegerExporter",
    "Meter",
    "NewRelicExporter",
    "ObservabilityMiddleware",
    "OtelCounter",
    "OtelGauge",
    "OtelHistogram",
    "OtelMeter",
    "OtelSpan",
    "OtelTracer",
    "OtelUpDownCounter",
    "OtlpExporter",
    "PreparedExporter",
    "PrometheusExporter",
    "Span",
    "SpanKind",
    "SpanStatus",
    "SplunkExporter",
    "TelemetryContext",
    "TelemetryProvider",
    "TraceContext",
    "Tracer",
    "UpDownCounter",
    "ZipkinExporter",
    "build_diagnostic_report",
    "get_logger",
    "get_telemetry_context",
    "set_telemetry_context",
    # -- Plataforma de protección de APIs (Sprint 2.9, ADR-009).
    "ApiAudit",
    "ApiAuditMiddleware",
    "ApiAuditRecord",
    "ApiGateway",
    "ApiOutcome",
    "ApiProtectionConfiguration",
    "ApiProtectionException",
    "ApiProtectionModule",
    "ApiProtectionPolicy",
    "ApiRequestContext",
    "ApiVersion",
    "ApiVersionMiddleware",
    "ApiVersionNegotiator",
    "ApiVersioningPolicy",
    "AuditSink",
    "BrotliCompressionProvider",
    "CompressionAlgorithm",
    "CompressionMiddleware",
    "CompressionNegotiator",
    "CompressionPolicy",
    "CompressionProvider",
    "CorsMiddleware",
    "CorsPolicy",
    "DEFAULT_IDEMPOTENT_METHODS",
    "FixedWindowAlgorithm",
    "GatewayDecision",
    "GzipCompressionProvider",
    "IdempotencyConflictException",
    "IdempotencyManager",
    "IdempotencyMiddleware",
    "IdempotencyRecord",
    "IdempotencyStore",
    "InMemoryAuditSink",
    "InMemoryIdempotencyStore",
    "InMemoryQuotaStore",
    "InMemoryRateLimitStore",
    "InvalidRequestException",
    "LeakyBucketAlgorithm",
    "LoggingAuditSink",
    "MIDDLEWARE_ORDER",
    "ProtectionScope",
    "QuotaDecision",
    "QuotaExceededException",
    "QuotaKind",
    "QuotaManager",
    "QuotaMiddleware",
    "QuotaPeriod",
    "QuotaRule",
    "QuotaStore",
    "QuotaUsage",
    "RateLimitAlgorithm",
    "RateLimitAlgorithmBase",
    "RateLimitDecision",
    "RateLimitExceededException",
    "RateLimitMiddleware",
    "RateLimitRule",
    "RateLimitState",
    "RateLimitStore",
    "RateLimiter",
    "RedisIdempotencyStore",
    "RedisQuotaStore",
    "RedisRateLimitStore",
    "RequestTooLargeException",
    "RequestValidationMiddleware",
    "RequestValidationPolicy",
    "RequestValidator",
    "ResponseTooLargeException",
    "SlidingWindowAlgorithm",
    "TokenBucketAlgorithm",
    "UnsupportedApiVersionException",
    "UnsupportedContentTypeException",
    "VersionNegotiation",
    "VersioningStrategy",
    "build_audit_record",
    "build_fingerprint",
    "build_request_context",
    "get_algorithm",
    "parse_accept_encoding",
}


def test_all_is_defined_explicitly() -> None:
    assert hasattr(teaf, "__all__")
    assert isinstance(teaf.__all__, list)


def test_all_matches_the_expected_public_surface_exactly() -> None:
    """Ni de más ni de menos — la superficie pública es intencional, no accidental."""
    assert set(teaf.__all__) == _EXPECTED_ALL


def test_all_has_no_duplicates() -> None:
    assert len(teaf.__all__) == len(set(teaf.__all__))


def test_every_symbol_in_all_is_actually_importable() -> None:
    for name in teaf.__all__:
        assert hasattr(teaf, name), f"'{name}' está en __all__ pero no es un atributo de teaf"


def test_module_is_an_alias_of_module_base_not_a_distinct_class() -> None:
    assert teaf.Module is teaf.ModuleBase


def test_health_is_an_alias_of_capability_health() -> None:
    from teaf._internal.runtime.capabilities.enums import CapabilityHealth

    assert teaf.Health is CapabilityHealth


def test_configuration_is_an_alias_of_settings() -> None:
    from teaf._internal.config.settings import Settings

    assert teaf.Configuration is Settings


def test_version_is_the_already_built_instance_not_the_class() -> None:
    from teaf.version import Version as VersionClass

    assert isinstance(teaf.Version, VersionClass)


def test_no_backend_symbols_leak_at_top_level() -> None:
    """``teaf`` no reexporta accidentalmente ningún módulo ``backend`` como atributo propio."""
    for name in dir(teaf):
        if name.startswith("_"):
            continue
        value = getattr(teaf, name)
        module_name = getattr(value, "__module__", "")
        # Los símbolos reexportados viven físicamente en backend.* (eso es
        # esperado e intencional) — lo que no debe ocurrir es que el propio
        # paquete "backend" o uno de sus submódulos quede expuesto como
        # atributo navegable de teaf (p. ej. teaf.backend).
        assert name not in {"backend"}
        assert module_name != "backend"
