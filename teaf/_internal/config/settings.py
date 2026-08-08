"""Configuración tipada por entorno (Configuration by Environment).

Cada entorno (``development``/``testing``/``staging``/``production``) tiene
su propia subclase de ``Settings`` con valores por defecto sensatos para ese
entorno; cualquier valor puede sobrescribirse vía variable de entorno o
archivo ``.env`` (ver ``.env.example`` en la raíz), nunca hardcodeado.

Añadir un parámetro de configuración nuevo es tan simple como declarar un
campo tipado más en ``Settings`` — no requiere tocar ``environment.py`` ni el
resto del framework (ver docs/core/CORE.md, "Cómo extender el Core").
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from teaf._internal.config.environment import Environment, get_environment
from teaf._internal.core.logging import LogFormat
from teaf._internal.security.tokens.jwt_policy import describe_secret_violation


class Settings(BaseSettings):
    """Configuración base. No se instancia directamente: usar ``get_settings()``."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TEAF"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # Preparado para Azure App Service / Docker / Render: ambos inyectan
    # PORT en runtime; HOST 0.0.0.0 es obligatorio para escuchar dentro de
    # un contenedor.
    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"
    log_format: LogFormat = "console"
    log_file: str | None = None

    docs_enabled: bool = True

    # -- Seguridad (Sprint 2.7, ADR-007) -------------------------------------------------
    #
    # Superficie de configuración por entorno para la plataforma de seguridad
    # (``teaf.security`` / ``teaf/_internal/security/``). Deliberadamente
    # desacoplada de ``SecurityConfiguration``/``SecurityModule``
    # (``teaf/_internal/modules/security/configuration.py``) — ese módulo no
    # importa ``config/`` (ver su docstring, "mantener la independencia del
    # resto de sdk/"); una aplicación concreta es quien decide si construye
    # ``SecurityConfiguration`` a partir de estos campos
    # (``SecurityConfiguration.from_mapping(settings.model_dump())``) o de
    # otra fuente. Solo campos escalares, mismo estilo que el resto de esta
    # clase — sin sub-modelos anidados.

    # JWT
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "teaf"
    jwt_audience: str = "teaf"

    # Expiración de tokens / Refresh Tokens
    jwt_access_token_ttl_seconds: int = 900
    jwt_refresh_token_ttl_seconds: int = 1_209_600
    jwt_clock_skew_seconds: int = 30

    # API Keys
    api_key_header: str = "X-API-Key"
    api_key_query_param: str = "api_key"
    api_key_hash_secret: str | None = None

    # LDAP / Active Directory — ``None`` significa "sin configurar"; una
    # aplicación que no use LDAP simplemente no construye ``LDAPIdentityProvider``.
    ldap_server_uri: str | None = None
    ldap_base_dn: str | None = None
    ldap_user_dn_template: str | None = None
    ldap_group_search_base: str | None = None
    ldap_group_search_filter: str = "(member={user_dn})"
    ldap_use_ssl: bool = True

    # Azure AD (Microsoft Entra ID)
    azure_ad_tenant: str | None = None
    azure_ad_client_id: str | None = None
    azure_ad_client_secret: str | None = None
    #: Tenants permitidos cuando ``azure_ad_tenant`` es multi-tenant
    #: (``"common"``/``"organizations"``/``"consumers"``) — lista separada
    #: por comas (p. ej. ``"tenant-a,tenant-b"``), ``None`` = cualquier tenant.
    azure_ad_allowed_tenants: str | None = None

    # Multi Tenant
    multi_tenant_enabled: bool = False
    default_tenant_id: str | None = None

    # Política de contraseñas
    password_hasher: str = "argon2"
    password_min_length: int = 12
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4
    bcrypt_rounds: int = 12

    # Rotación de secretos
    secret_rotation_enabled: bool = False
    secret_rotation_interval_days: int = 90

    @model_validator(mode="after")
    def _validate_jwt_secret(self) -> Settings:
        """Rechaza un secreto JWT más corto de lo que exige RFC 7518 §3.2.

        Se valida aquí —al construir la configuración, antes de que la
        aplicación arranque— y no al firmar el primer token: un secreto
        débil es un error de despliegue, y el momento de descubrirlo es el
        arranque, no la primera petición autenticada en producción.

        ``jwt_secret=None`` sigue significando «JWT sin configurar» y no
        valida nada: una aplicación que no use JWT no tiene por qué
        declarar un secreto. La misma política se aplica en
        ``JWTTokenProvider.__init__`` para quien lo construya a mano, que es
        la otra vía por la que un secreto llega al framework (Sprint 3.0).
        """
        violation = describe_secret_violation(self.jwt_secret, self.jwt_algorithm)
        if violation is not None:
            raise ValueError(violation)
        return self

    # -- Cabeceras de seguridad HTTP (Sprint 2.9.2, ADR-010) -----------------------------
    #
    # Las consume ``SecurityHeadersMiddleware``
    # (``teaf/_internal/middleware/security_headers.py``), que ``create_app``
    # instala siempre. Hasta Sprint 2.9.2 estos campos existían sin que nadie
    # los leyera: prometían una protección inexistente. Ver
    # [SECURITY-STANDARD.md §7](../../../docs/standards/SECURITY-STANDARD.md).

    security_headers_enabled: bool = True
    #: ``max-age`` de ``Strict-Transport-Security``, en segundos (por defecto, un año).
    #: La cabecera **solo se emite sobre HTTPS**, como exige RFC 6797 §7.2.
    security_hsts_max_age_seconds: int = 31_536_000
    #: Valor de ``X-Frame-Options``. Cadena vacía omite la cabecera (la
    #: directiva ``frame-ancestors`` de la CSP la sustituye en navegadores
    #: modernos, y ``X-Frame-Options`` solo sigue ahí por los antiguos).
    security_frame_options: str = "DENY"
    #: ``Content-Security-Policy``. El valor por defecto es el correcto para
    #: una API JSON —prohíbe cargar cualquier recurso y ser embebida—, no para
    #: un frontend: una aplicación que sirva HTML propio debe sustituirlo por
    #: la política de su frontend (ver SECURITY-STANDARD.md §7).
    security_content_security_policy: str = "default-src 'none'; frame-ancestors 'none'"

    # -- Caché distribuida (Sprint 3.0, ADR-012) -----------------------------------------
    #
    # Mismo criterio que el resto: superficie de configuración por entorno,
    # desacoplada de ``CacheConfiguration``/``CacheModule``
    # (``teaf/_internal/modules/cache/configuration.py``), que la reconoce por
    # el prefijo ``cache_`` vía ``from_mapping(settings.model_dump())``.
    #
    # Desactivada por defecto: TEAF debe arrancar sin infraestructura.

    cache_enabled: bool = False
    #: ``memory`` (un proceso, sin infraestructura) o ``redis`` (compartida
    #: entre réplicas — requiere el extra ``teaf[redis]``).
    cache_backend: str = "memory"
    #: URL de conexión. ``rediss://`` activa TLS. **Contiene credenciales**:
    #: debe venir de una variable de entorno o de un gestor de secretos.
    cache_redis_url: str = "redis://localhost:6379/0"
    cache_key_prefix: str = "teaf"
    cache_connect_timeout_seconds: float = 5.0
    cache_operation_timeout_seconds: float = 5.0
    cache_max_connections: int = 10
    #: Verificación del certificado TLS. Desactivarla expone la conexión a un
    #: intermediario; solo tiene sentido contra un Redis de desarrollo.
    cache_tls_verify: bool = True

    # -- Observabilidad (Sprint 2.8, ADR-008) --------------------------------------------
    #
    # Mismo criterio que la sección de Seguridad de arriba: superficie de
    # configuración por entorno, deliberadamente desacoplada de
    # ``ObservabilityConfiguration``/``ObservabilityModule``
    # (``teaf/_internal/modules/observability/configuration.py``) — una
    # aplicación concreta decide si construye esa configuración a partir de
    # estos campos (``ObservabilityConfiguration.from_mapping(settings.model_dump())``)
    # o de otra fuente.

    observability_service_version: str = "0.0.0"
    observability_tracing_enabled: bool = True
    observability_metrics_enabled: bool = True
    observability_sampling_ratio: float = 1.0

    observability_console_exporter_enabled: bool = True
    observability_otlp_exporter_enabled: bool = False
    observability_otlp_traces_endpoint: str | None = None
    observability_otlp_metrics_endpoint: str | None = None
    observability_otlp_timeout_seconds: float | None = None
    observability_prometheus_exporter_enabled: bool = False
    observability_prometheus_prefix: str = ""
    observability_metrics_export_interval_millis: int = 60_000

    # -- Protección de APIs (Sprint 2.9, ADR-009) ----------------------------------------
    #
    # Mismo criterio que las dos secciones anteriores: superficie de
    # configuración por entorno, desacoplada de ``ApiProtectionConfiguration``/
    # ``ApiProtectionModule`` (``teaf/_internal/api/module/configuration.py``).
    # La diferencia con Seguridad/Observabilidad es que aquí los nombres sí
    # coinciden campo a campo con los de esa configuración, salvo por el
    # prefijo ``api_``: ``ApiProtectionConfiguration.from_mapping`` lo
    # reconoce, así que ``from_mapping(settings.model_dump())`` funciona sin
    # transformar nada.
    #
    # Las listas viajan como cadenas separadas por comas porque una variable
    # de entorno no puede ser otra cosa (``API_CORS_ALLOW_ORIGINS=
    # "https://a.com,https://b.com"``); ``_coerce_tuple`` las convierte.

    # Rate limiting
    api_rate_limit_enabled: bool = True
    api_rate_limit_requests: int = 1_000
    api_rate_limit_window_seconds: float = 60.0
    api_rate_limit_algorithm: str = "fixed_window"
    api_rate_limit_scope: str = "ip"
    api_rate_limit_burst: int = 0

    # Quotas — cada límite a 0 significa "sin cuota de ese tipo".
    api_quotas_enabled: bool = False
    api_quota_scope: str = "tenant"
    api_quota_requests_per_minute: int = 0
    api_quota_requests_per_hour: int = 0
    api_quota_requests_per_day: int = 0
    api_quota_requests_per_month: int = 0
    api_quota_bandwidth_bytes_per_day: int = 0
    api_quota_max_payload_bytes: int = 0
    api_quota_max_concurrent_requests: int = 0

    # CORS — sin orígenes declarados, CORS queda desactivado.
    api_cors_allow_origins: str = ""
    api_cors_allow_origin_patterns: str = ""
    api_cors_allow_methods: str = "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS"
    api_cors_allow_headers: str = ""
    api_cors_expose_headers: str = ""
    api_cors_allow_credentials: bool = False
    api_cors_max_age_seconds: int = 600

    # Versionado
    api_versioning_enabled: bool = True
    api_versioning_supported: str = "v1"
    api_versioning_default: str = "v1"
    api_versioning_strategies: str = "uri,header,media_type"
    api_versioning_header: str = "X-API-Version"
    api_versioning_media_type_vendor: str = "teaf"
    api_versioning_strict: bool = True

    # Validación de peticiones
    api_validation_enabled: bool = True
    api_validation_max_request_bytes: int = 10 * 1024 * 1024
    api_validation_max_response_bytes: int = 50 * 1024 * 1024
    api_validation_validate_responses: bool = False
    api_validation_allowed_content_types: str = ""
    api_validation_required_headers: str = ""
    api_validation_blocked_user_agents: str = ""
    api_validation_allowed_user_agents: str = ""
    api_validation_require_user_agent: bool = False
    api_validation_max_url_length: int = 8_000

    # Compresión
    api_compression_enabled: bool = True
    api_compression_minimum_size_bytes: int = 500
    api_compression_gzip_enabled: bool = True
    api_compression_gzip_level: int = 6
    api_compression_brotli_enabled: bool = True
    api_compression_brotli_quality: int = 4

    # Idempotencia
    api_idempotency_enabled: bool = False
    api_idempotency_ttl_seconds: float = 86_400.0
    api_idempotency_header: str = "Idempotency-Key"
    api_idempotency_methods: str = "POST,PATCH"

    # Auditoría de API
    api_audit_enabled: bool = True
    api_audit_memory_sink_enabled: bool = True
    api_audit_memory_sink_limit: int = 1_000
    api_audit_logging_sink_enabled: bool = False

    #: ``False`` cuando la aplicación se expone directamente a internet: sin un
    #: proxy que las reescriba, ``X-Forwarded-For`` la controla el cliente y
    #: falsearla saltaría cualquier límite por IP (ver docs/api/RATE-LIMITING.md).
    #: **Deprecado en Sprint 3.0** a favor de ``api_trusted_proxies`` (ADR-011).
    #: Se mantiene por compatibilidad y solo se consulta cuando
    #: ``api_trusted_proxies`` está vacío.
    api_trust_forwarded_headers: bool = True
    #: Redes de proxy cuyas cabeceras de reenvío son creíbles, separadas por
    #: comas: ``API_TRUSTED_PROXIES="10.0.0.0/8,192.168.1.10"``. Acepta IPs
    #: sueltas y CIDR, IPv4 e IPv6. Configurarlo desactiva
    #: ``api_trust_forwarded_headers``: se pasa de confiar a ciegas a confiar
    #: solo en proxies conocidos, que es lo que impide la falsificación de
    #: ``X-Forwarded-For`` (ver docs/security/SECURITY-CONFIGURATION.md).
    api_trusted_proxies: str = ""


class DevelopmentSettings(Settings):
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "DEBUG"
    log_format: LogFormat = "console"
    docs_enabled: bool = True


class TestingSettings(Settings):
    environment: Environment = Environment.TESTING
    debug: bool = True
    log_level: str = "WARNING"
    log_format: LogFormat = "console"
    docs_enabled: bool = True
    #: Coste de Argon2id reducido — evita ralentizar la suite de pruebas
    #: (ver ``Argon2PasswordHasher``, docs/security/... y CODING-STANDARD.md).
    argon2_time_cost: int = 1
    argon2_memory_cost: int = 8
    argon2_parallelism: int = 1
    bcrypt_rounds: int = 4


class StagingSettings(Settings):
    environment: Environment = Environment.STAGING
    debug: bool = False
    log_level: str = "INFO"
    log_format: LogFormat = "json"
    docs_enabled: bool = True


class ProductionSettings(Settings):
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: str = "INFO"
    log_format: LogFormat = "json"
    #: Swagger/OpenAPI deshabilitado por defecto en producción.
    docs_enabled: bool = False
    #: Rotación de secretos activada por defecto en producción (ver
    #: SECURITY-STANDARD.md) — el resto de entornos la dejan desactivada.
    secret_rotation_enabled: bool = True
    #: La auditoría de API va al log estructurado en producción (Sprint 2.9):
    #: es donde un agente de logs puede recogerla y retenerla, a diferencia
    #: del destino en memoria, que se pierde al reiniciar el proceso.
    api_audit_logging_sink_enabled: bool = True


_SETTINGS_BY_ENVIRONMENT: dict[Environment, type[Settings]] = {
    Environment.DEVELOPMENT: DevelopmentSettings,
    Environment.TESTING: TestingSettings,
    Environment.STAGING: StagingSettings,
    Environment.PRODUCTION: ProductionSettings,
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Resuelve la configuración de la instancia en ejecución (cacheada por proceso).

    Selecciona la subclase de ``Settings`` según ``ENVIRONMENT`` y aplica
    sobre ella cualquier variable de entorno / ``.env`` presente.
    """
    environment = get_environment()
    settings_cls = _SETTINGS_BY_ENVIRONMENT[environment]
    return settings_cls()
