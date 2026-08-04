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

from pydantic_settings import BaseSettings, SettingsConfigDict

from teaf._internal.config.environment import Environment, get_environment
from teaf._internal.core.logging import LogFormat


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

    # Cabeceras de seguridad HTTP
    security_headers_enabled: bool = True
    security_hsts_max_age_seconds: int = 31_536_000
    security_frame_options: str = "DENY"

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
