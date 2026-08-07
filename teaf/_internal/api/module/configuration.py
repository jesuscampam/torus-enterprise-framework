"""``ApiProtectionConfiguration`` — configuración del ``ApiProtectionModule`` (Sprint 2.9).

Mismo criterio que ``modules/security/configuration.py`` y
``modules/observability/configuration.py``: se resuelve desde un ``Mapping``
(``from_mapping``) y no importa ``config/`` directamente, para mantener la
independencia del resto de ``sdk/``. La única diferencia es una comodidad
añadida: ``from_mapping`` acepta tanto la clave desnuda (``rate_limit_enabled``)
como la prefijada (``api_rate_limit_enabled``), de forma que
``ApiProtectionConfiguration.from_mapping(settings.model_dump())`` funciona
sin transformar nada — los campos de ``Settings`` llevan el prefijo ``api_``
para no colisionar con los de seguridad y observabilidad.

Todo es escalar (``bool``/``int``/``float``/``str``/tuplas de ``str``), igual
que ``Settings``: las reglas estructuradas (``RateLimitRule``/``QuotaRule``)
se derivan de estos escalares en ``build_rate_limit_rules``/
``build_quota_rules``, o se pasan a mano al construir el módulo cuando una
aplicación necesita más de una regla por dimensión.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from teaf._internal.api.models import (
    ApiVersion,
    ProtectionScope,
    QuotaKind,
    QuotaPeriod,
    QuotaRule,
    RateLimitAlgorithm,
    RateLimitRule,
    VersioningStrategy,
)

_PREFIX = "api_"


def _lookup(values: Mapping[str, object], key: str) -> object:
    """Valor de ``key``, buscando primero la variante prefijada con ``api_``."""
    prefixed = values.get(f"{_PREFIX}{key}")
    return prefixed if prefixed is not None else values.get(key)


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_int(value: object, default: int) -> int:
    return default if value is None else int(str(value))


def _coerce_float(value: object, default: float) -> float:
    return default if value is None else float(str(value))


def _coerce_str(value: object, default: str) -> str:
    return default if value is None else str(value)


def _coerce_tuple(value: object, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Interpreta una lista separada por comas —o una secuencia ya tipada— como tupla.

    Las variables de entorno solo saben de cadenas, así que
    ``API_CORS_ALLOW_ORIGINS="https://a.com,https://b.com"`` debe producir
    lo mismo que pasar la tupla directamente desde código.
    """
    if value is None:
        return default
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(part).strip() for part in value if str(part).strip())
    return default


@dataclass(frozen=True, slots=True)
class ApiProtectionConfiguration:
    """Configuración escalar de los ocho subsistemas de protección.

    Los valores por defecto están elegidos para que activar el módulo no
    cambie el comportamiento observable de una aplicación existente: rate
    limiting y auditoría activos pero generosos, compresión activa (solo
    afecta al tamaño en red), y cuotas, CORS, versionado estricto e
    idempotencia **desactivados** hasta que se declaren.
    """

    # -- Rate limiting --------------------------------------------------------------
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1_000
    rate_limit_window_seconds: float = 60.0
    rate_limit_algorithm: str = RateLimitAlgorithm.FIXED_WINDOW.value
    rate_limit_scope: str = ProtectionScope.IP.value
    rate_limit_burst: int = 0

    # -- Quotas ---------------------------------------------------------------------
    quotas_enabled: bool = False
    quota_scope: str = ProtectionScope.TENANT.value
    quota_requests_per_minute: int = 0
    quota_requests_per_hour: int = 0
    quota_requests_per_day: int = 0
    quota_requests_per_month: int = 0
    quota_bandwidth_bytes_per_day: int = 0
    quota_max_payload_bytes: int = 0
    quota_max_concurrent_requests: int = 0

    # -- CORS -----------------------------------------------------------------------
    cors_allow_origins: tuple[str, ...] = ()
    cors_allow_origin_patterns: tuple[str, ...] = ()
    cors_allow_methods: tuple[str, ...] = (
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    )
    cors_allow_headers: tuple[str, ...] = ()
    cors_expose_headers: tuple[str, ...] = ()
    cors_allow_credentials: bool = False
    cors_max_age_seconds: int = 600

    # -- Versionado -----------------------------------------------------------------
    versioning_enabled: bool = True
    versioning_supported: tuple[str, ...] = ("v1",)
    versioning_default: str = "v1"
    versioning_strategies: tuple[str, ...] = ("uri", "header", "media_type")
    versioning_header: str = "X-API-Version"
    versioning_media_type_vendor: str = "teaf"
    versioning_strict: bool = True

    # -- Validación -----------------------------------------------------------------
    validation_enabled: bool = True
    validation_max_request_bytes: int = 10 * 1024 * 1024
    validation_max_response_bytes: int = 50 * 1024 * 1024
    validation_validate_responses: bool = False
    validation_allowed_content_types: tuple[str, ...] = ()
    validation_required_headers: tuple[str, ...] = ()
    validation_blocked_user_agents: tuple[str, ...] = ()
    validation_allowed_user_agents: tuple[str, ...] = ()
    validation_require_user_agent: bool = False
    validation_max_url_length: int = 8_000

    # -- Compresión -----------------------------------------------------------------
    compression_enabled: bool = True
    compression_minimum_size_bytes: int = 500
    compression_gzip_enabled: bool = True
    compression_gzip_level: int = 6
    compression_brotli_enabled: bool = True
    compression_brotli_quality: int = 4

    # -- Idempotencia ---------------------------------------------------------------
    idempotency_enabled: bool = False
    idempotency_ttl_seconds: float = 86_400.0
    idempotency_header: str = "Idempotency-Key"
    idempotency_methods: tuple[str, ...] = ("POST", "PATCH")

    # -- Auditoría ------------------------------------------------------------------
    audit_enabled: bool = True
    audit_memory_sink_enabled: bool = True
    audit_memory_sink_limit: int = 1_000
    audit_logging_sink_enabled: bool = False

    # -- Transversal ----------------------------------------------------------------
    #: ``False`` cuando la aplicación está expuesta directamente a internet:
    #: sin un proxy que las reescriba, las cabeceras ``X-Forwarded-For`` las
    #: controla el cliente y falsearlas saltaría cualquier límite por IP.
    trust_forwarded_headers: bool = True
    #: Redes de proxy de confianza (IP o CIDR). Ver ADR-011.
    trusted_proxies: tuple[str, ...] = ()

    @property
    def algorithm(self) -> RateLimitAlgorithm:
        """``rate_limit_algorithm`` como enum (cae a ventana fija si no se reconoce)."""
        try:
            return RateLimitAlgorithm(self.rate_limit_algorithm)
        except ValueError:
            return RateLimitAlgorithm.FIXED_WINDOW

    @property
    def scope(self) -> ProtectionScope:
        """``rate_limit_scope`` como enum (cae a IP si no se reconoce)."""
        try:
            return ProtectionScope(self.rate_limit_scope)
        except ValueError:
            return ProtectionScope.IP

    @property
    def quota_protection_scope(self) -> ProtectionScope:
        """``quota_scope`` como enum (cae a tenant si no se reconoce)."""
        try:
            return ProtectionScope(self.quota_scope)
        except ValueError:
            return ProtectionScope.TENANT

    @property
    def versioning_strategy_enums(self) -> tuple[VersioningStrategy, ...]:
        """``versioning_strategies`` como enums, descartando los no reconocidos."""
        strategies: list[VersioningStrategy] = []
        for value in self.versioning_strategies:
            try:
                strategies.append(VersioningStrategy(value.strip().lower()))
            except ValueError:
                continue
        return tuple(strategies)

    @property
    def supported_versions(self) -> tuple[ApiVersion, ...]:
        """``versioning_supported`` como ``ApiVersion``, descartando los no válidos."""
        versions: list[ApiVersion] = []
        for value in self.versioning_supported:
            try:
                versions.append(ApiVersion.parse(value))
            except ValueError:
                continue
        return tuple(versions) or (ApiVersion(1),)

    @property
    def default_version(self) -> ApiVersion:
        """``versioning_default`` como ``ApiVersion`` (cae a la primera soportada)."""
        try:
            return ApiVersion.parse(self.versioning_default)
        except ValueError:
            return self.supported_versions[0]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> ApiProtectionConfiguration:
        """Construye la configuración desde un ``Mapping`` (claves ausentes usan el default)."""
        defaults = cls()
        return cls(
            rate_limit_enabled=_coerce_bool(
                _lookup(values, "rate_limit_enabled"), defaults.rate_limit_enabled
            ),
            rate_limit_requests=_coerce_int(
                _lookup(values, "rate_limit_requests"), defaults.rate_limit_requests
            ),
            rate_limit_window_seconds=_coerce_float(
                _lookup(values, "rate_limit_window_seconds"), defaults.rate_limit_window_seconds
            ),
            rate_limit_algorithm=_coerce_str(
                _lookup(values, "rate_limit_algorithm"), defaults.rate_limit_algorithm
            ),
            rate_limit_scope=_coerce_str(
                _lookup(values, "rate_limit_scope"), defaults.rate_limit_scope
            ),
            rate_limit_burst=_coerce_int(
                _lookup(values, "rate_limit_burst"), defaults.rate_limit_burst
            ),
            quotas_enabled=_coerce_bool(_lookup(values, "quotas_enabled"), defaults.quotas_enabled),
            quota_scope=_coerce_str(_lookup(values, "quota_scope"), defaults.quota_scope),
            quota_requests_per_minute=_coerce_int(
                _lookup(values, "quota_requests_per_minute"), defaults.quota_requests_per_minute
            ),
            quota_requests_per_hour=_coerce_int(
                _lookup(values, "quota_requests_per_hour"), defaults.quota_requests_per_hour
            ),
            quota_requests_per_day=_coerce_int(
                _lookup(values, "quota_requests_per_day"), defaults.quota_requests_per_day
            ),
            quota_requests_per_month=_coerce_int(
                _lookup(values, "quota_requests_per_month"), defaults.quota_requests_per_month
            ),
            quota_bandwidth_bytes_per_day=_coerce_int(
                _lookup(values, "quota_bandwidth_bytes_per_day"),
                defaults.quota_bandwidth_bytes_per_day,
            ),
            quota_max_payload_bytes=_coerce_int(
                _lookup(values, "quota_max_payload_bytes"), defaults.quota_max_payload_bytes
            ),
            quota_max_concurrent_requests=_coerce_int(
                _lookup(values, "quota_max_concurrent_requests"),
                defaults.quota_max_concurrent_requests,
            ),
            cors_allow_origins=_coerce_tuple(
                _lookup(values, "cors_allow_origins"), defaults.cors_allow_origins
            ),
            cors_allow_origin_patterns=_coerce_tuple(
                _lookup(values, "cors_allow_origin_patterns"), defaults.cors_allow_origin_patterns
            ),
            cors_allow_methods=_coerce_tuple(
                _lookup(values, "cors_allow_methods"), defaults.cors_allow_methods
            ),
            cors_allow_headers=_coerce_tuple(
                _lookup(values, "cors_allow_headers"), defaults.cors_allow_headers
            ),
            cors_expose_headers=_coerce_tuple(
                _lookup(values, "cors_expose_headers"), defaults.cors_expose_headers
            ),
            cors_allow_credentials=_coerce_bool(
                _lookup(values, "cors_allow_credentials"), defaults.cors_allow_credentials
            ),
            cors_max_age_seconds=_coerce_int(
                _lookup(values, "cors_max_age_seconds"), defaults.cors_max_age_seconds
            ),
            versioning_enabled=_coerce_bool(
                _lookup(values, "versioning_enabled"), defaults.versioning_enabled
            ),
            versioning_supported=_coerce_tuple(
                _lookup(values, "versioning_supported"), defaults.versioning_supported
            ),
            versioning_default=_coerce_str(
                _lookup(values, "versioning_default"), defaults.versioning_default
            ),
            versioning_strategies=_coerce_tuple(
                _lookup(values, "versioning_strategies"), defaults.versioning_strategies
            ),
            versioning_header=_coerce_str(
                _lookup(values, "versioning_header"), defaults.versioning_header
            ),
            versioning_media_type_vendor=_coerce_str(
                _lookup(values, "versioning_media_type_vendor"),
                defaults.versioning_media_type_vendor,
            ),
            versioning_strict=_coerce_bool(
                _lookup(values, "versioning_strict"), defaults.versioning_strict
            ),
            validation_enabled=_coerce_bool(
                _lookup(values, "validation_enabled"), defaults.validation_enabled
            ),
            validation_max_request_bytes=_coerce_int(
                _lookup(values, "validation_max_request_bytes"),
                defaults.validation_max_request_bytes,
            ),
            validation_max_response_bytes=_coerce_int(
                _lookup(values, "validation_max_response_bytes"),
                defaults.validation_max_response_bytes,
            ),
            validation_validate_responses=_coerce_bool(
                _lookup(values, "validation_validate_responses"),
                defaults.validation_validate_responses,
            ),
            validation_allowed_content_types=_coerce_tuple(
                _lookup(values, "validation_allowed_content_types"),
                defaults.validation_allowed_content_types,
            ),
            validation_required_headers=_coerce_tuple(
                _lookup(values, "validation_required_headers"),
                defaults.validation_required_headers,
            ),
            validation_blocked_user_agents=_coerce_tuple(
                _lookup(values, "validation_blocked_user_agents"),
                defaults.validation_blocked_user_agents,
            ),
            validation_allowed_user_agents=_coerce_tuple(
                _lookup(values, "validation_allowed_user_agents"),
                defaults.validation_allowed_user_agents,
            ),
            validation_require_user_agent=_coerce_bool(
                _lookup(values, "validation_require_user_agent"),
                defaults.validation_require_user_agent,
            ),
            validation_max_url_length=_coerce_int(
                _lookup(values, "validation_max_url_length"), defaults.validation_max_url_length
            ),
            compression_enabled=_coerce_bool(
                _lookup(values, "compression_enabled"), defaults.compression_enabled
            ),
            compression_minimum_size_bytes=_coerce_int(
                _lookup(values, "compression_minimum_size_bytes"),
                defaults.compression_minimum_size_bytes,
            ),
            compression_gzip_enabled=_coerce_bool(
                _lookup(values, "compression_gzip_enabled"), defaults.compression_gzip_enabled
            ),
            compression_gzip_level=_coerce_int(
                _lookup(values, "compression_gzip_level"), defaults.compression_gzip_level
            ),
            compression_brotli_enabled=_coerce_bool(
                _lookup(values, "compression_brotli_enabled"), defaults.compression_brotli_enabled
            ),
            compression_brotli_quality=_coerce_int(
                _lookup(values, "compression_brotli_quality"), defaults.compression_brotli_quality
            ),
            idempotency_enabled=_coerce_bool(
                _lookup(values, "idempotency_enabled"), defaults.idempotency_enabled
            ),
            idempotency_ttl_seconds=_coerce_float(
                _lookup(values, "idempotency_ttl_seconds"), defaults.idempotency_ttl_seconds
            ),
            idempotency_header=_coerce_str(
                _lookup(values, "idempotency_header"), defaults.idempotency_header
            ),
            idempotency_methods=_coerce_tuple(
                _lookup(values, "idempotency_methods"), defaults.idempotency_methods
            ),
            audit_enabled=_coerce_bool(_lookup(values, "audit_enabled"), defaults.audit_enabled),
            audit_memory_sink_enabled=_coerce_bool(
                _lookup(values, "audit_memory_sink_enabled"), defaults.audit_memory_sink_enabled
            ),
            audit_memory_sink_limit=_coerce_int(
                _lookup(values, "audit_memory_sink_limit"), defaults.audit_memory_sink_limit
            ),
            audit_logging_sink_enabled=_coerce_bool(
                _lookup(values, "audit_logging_sink_enabled"), defaults.audit_logging_sink_enabled
            ),
            trusted_proxies=_coerce_tuple(
                _lookup(values, "trusted_proxies"), defaults.trusted_proxies
            ),
            trust_forwarded_headers=_coerce_bool(
                _lookup(values, "trust_forwarded_headers"), defaults.trust_forwarded_headers
            ),
        )


def build_rate_limit_rules(
    configuration: ApiProtectionConfiguration,
) -> tuple[RateLimitRule, ...]:
    """Regla de limitación derivada de la configuración escalar.

    Devuelve como mucho una regla: la configuración por variables de entorno
    cubre el caso "un límite global"; una aplicación con varias reglas las
    pasa directamente a ``ApiProtectionModule(rate_limit_rules=[...])``, que
    es más expresivo que intentar codificarlas en cadenas de entorno.
    """
    if not configuration.rate_limit_enabled or configuration.rate_limit_requests <= 0:
        return ()
    return (
        RateLimitRule(
            name="default",
            limit=configuration.rate_limit_requests,
            window_seconds=configuration.rate_limit_window_seconds,
            algorithm=configuration.algorithm,
            scope=configuration.scope,
            burst=configuration.rate_limit_burst or None,
        ),
    )


def build_quota_rules(configuration: ApiProtectionConfiguration) -> tuple[QuotaRule, ...]:
    """Cuotas derivadas de la configuración escalar (solo las que tengan límite > 0)."""
    if not configuration.quotas_enabled:
        return ()

    scope = configuration.quota_protection_scope
    candidates: tuple[tuple[str, QuotaKind, int, QuotaPeriod], ...] = (
        (
            "requests-per-minute",
            QuotaKind.REQUESTS,
            configuration.quota_requests_per_minute,
            QuotaPeriod.MINUTE,
        ),
        (
            "requests-per-hour",
            QuotaKind.REQUESTS,
            configuration.quota_requests_per_hour,
            QuotaPeriod.HOUR,
        ),
        (
            "requests-per-day",
            QuotaKind.REQUESTS,
            configuration.quota_requests_per_day,
            QuotaPeriod.DAY,
        ),
        (
            "requests-per-month",
            QuotaKind.REQUESTS,
            configuration.quota_requests_per_month,
            QuotaPeriod.MONTH,
        ),
        (
            "bandwidth-per-day",
            QuotaKind.BANDWIDTH,
            configuration.quota_bandwidth_bytes_per_day,
            QuotaPeriod.DAY,
        ),
        (
            "max-payload",
            QuotaKind.PAYLOAD,
            configuration.quota_max_payload_bytes,
            QuotaPeriod.DAY,
        ),
        (
            "max-concurrent",
            QuotaKind.CONCURRENT,
            configuration.quota_max_concurrent_requests,
            QuotaPeriod.MINUTE,
        ),
    )
    return tuple(
        QuotaRule(name=name, kind=kind, limit=limit, period=period, scope=scope)
        for name, kind, limit, period in candidates
        if limit > 0
    )
