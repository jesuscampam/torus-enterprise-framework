"""``teaf.api`` — la plataforma de protección y gobernanza de APIs de TEAF (Sprint 2.9).

Ver ADR-009 (docs/architecture/adr/ADR-009-enterprise-api-protection.md) para el detalle
de cada decisión.

Fachada sobre ``teaf/_internal/api/`` (los ocho subsistemas de protección,
sus middlewares y el módulo que los empaqueta) y
``teaf/_internal/contracts/api.py`` (los contratos sobre los que se diseña
todo lo anterior) — un consumidor de TEAF nunca importa
``teaf._internal.api.*`` ni ``teaf._internal.contracts.api`` directamente,
solo ``from teaf.api import ...`` (o ``from teaf import ...``, ver
``teaf/__init__.py``).

``ApiGateway`` es la pieza que casi siempre se usa: compone los ocho
subsistemas y los instala sobre una aplicación con una sola llamada
(``gateway.install(app)``). El resto se expone porque cada subsistema es
utilizable por separado — un ``RateLimiter`` protegiendo un consumidor de
cola, un ``CorsPolicy`` evaluado en una prueba, un ``ApiAudit`` alimentado
desde un job.

Excepción deliberada a la regla de "ningún módulo real se expone desde
``teaf/``" (docs/public-api/PUBLIC-API.md, sección 6): ``ApiProtectionModule``
**sí** se exporta aquí, a diferencia de ``DatabaseModule``/``SecurityModule``/
``ObservabilityModule``. El motivo es que la protección de APIs se activa
como una unidad —los ocho subsistemas comparten configuración, orden de
middlewares y ciclo de vida—, así que obligar a recomponerla pieza a pieza
para usarla sería trabajo repetido en cada aplicación sin ninguna ganancia
de desacoplamiento. Componer manualmente sigue siendo posible: ese es
exactamente el resto de esta fachada.

Nota de nomenclatura:

- ``CompressionProvider`` es el **contrato**; ``GzipCompressionProvider`` y
  ``BrotliCompressionProvider`` son las implementaciones. GZip está
  disponible siempre (librería estándar); Brotli requiere el paquete
  opcional ``brotli``/``brotlicffi`` y, si falta, ``available`` es ``False``
  y el negociador simplemente no lo elige.
- ``ProtectionScope`` es una sola enumeración compartida por rate limiting y
  quotas: ambos agrupan por las mismas seis dimensiones (usuario, API Key,
  tenant, IP, endpoint, rol), así que duplicarla en dos enums sería
  exactamente el tipo de repetición que CLAUDE.md prohíbe.
- ``RateLimitStore``/``QuotaStore``/``IdempotencyStore``/``AuditSink`` son
  contratos ``async`` con implementación en memoria por defecto
  (``InMemory*``) y una variante Redis preparada — ver
  ``docs/api/API-PROTECTION.md``, "De memoria a Redis".
"""

from __future__ import annotations

from teaf._internal.api.audit.audit import ApiAudit, build_audit_record
from teaf._internal.api.compression.providers import (
    BrotliCompressionProvider,
    CompressionNegotiator,
    CompressionPolicy,
    GzipCompressionProvider,
    parse_accept_encoding,
)
from teaf._internal.api.cors.policy import CorsPolicy
from teaf._internal.api.exceptions import (
    ApiProtectionException,
    IdempotencyConflictException,
    InvalidRequestException,
    QuotaExceededException,
    RateLimitExceededException,
    RequestTooLargeException,
    ResponseTooLargeException,
    UnsupportedApiVersionException,
    UnsupportedContentTypeException,
)
from teaf._internal.api.gateway.gateway import MIDDLEWARE_ORDER, ApiGateway, GatewayDecision
from teaf._internal.api.idempotency.manager import (
    DEFAULT_IDEMPOTENT_METHODS,
    IdempotencyManager,
    build_fingerprint,
)
from teaf._internal.api.middleware.audit import ApiAuditMiddleware
from teaf._internal.api.middleware.compression import CompressionMiddleware
from teaf._internal.api.middleware.context import build_request_context
from teaf._internal.api.middleware.cors import CorsMiddleware
from teaf._internal.api.middleware.idempotency import IdempotencyMiddleware
from teaf._internal.api.middleware.quota import QuotaMiddleware
from teaf._internal.api.middleware.rate_limit import RateLimitMiddleware
from teaf._internal.api.middleware.validation import RequestValidationMiddleware
from teaf._internal.api.middleware.versioning import ApiVersionMiddleware
from teaf._internal.api.models import (
    ApiAuditRecord,
    ApiOutcome,
    ApiRequestContext,
    ApiVersion,
    CompressionAlgorithm,
    IdempotencyRecord,
    ProtectionScope,
    QuotaDecision,
    QuotaKind,
    QuotaPeriod,
    QuotaRule,
    QuotaUsage,
    RateLimitAlgorithm,
    RateLimitDecision,
    RateLimitRule,
    RateLimitState,
    VersioningStrategy,
    VersionNegotiation,
)
from teaf._internal.api.module.configuration import ApiProtectionConfiguration
from teaf._internal.api.module.module import ApiProtectionModule
from teaf._internal.api.providers.memory import (
    InMemoryAuditSink,
    InMemoryIdempotencyStore,
    InMemoryQuotaStore,
    InMemoryRateLimitStore,
    LoggingAuditSink,
)
from teaf._internal.api.providers.redis import (
    RedisIdempotencyStore,
    RedisQuotaStore,
    RedisRateLimitStore,
)
from teaf._internal.api.quotas.manager import QuotaManager
from teaf._internal.api.ratelimit.algorithms import (
    FixedWindowAlgorithm,
    LeakyBucketAlgorithm,
    RateLimitAlgorithmBase,
    SlidingWindowAlgorithm,
    TokenBucketAlgorithm,
    get_algorithm,
)
from teaf._internal.api.ratelimit.limiter import RateLimiter
from teaf._internal.api.validation.validator import RequestValidationPolicy, RequestValidator
from teaf._internal.api.versioning.negotiator import ApiVersioningPolicy, ApiVersionNegotiator
from teaf._internal.contracts.api import (
    ApiProtectionPolicy,
    AuditSink,
    CompressionProvider,
    IdempotencyStore,
    QuotaStore,
    RateLimitStore,
)

__all__ = [
    # -- El orquestador: compone e instala toda la cadena de protección -------------------------
    "ApiGateway",
    "GatewayDecision",
    "MIDDLEWARE_ORDER",
    "ApiProtectionModule",
    "ApiProtectionConfiguration",
    # -- Contexto de petición: el vocabulario común de toda la plataforma -----------------------
    "ApiRequestContext",
    "ProtectionScope",
    "build_request_context",
    # -- Rate limiting --------------------------------------------------------------------------
    "RateLimiter",
    "RateLimitRule",
    "RateLimitDecision",
    "RateLimitState",
    "RateLimitAlgorithm",
    "RateLimitAlgorithmBase",
    "FixedWindowAlgorithm",
    "SlidingWindowAlgorithm",
    "TokenBucketAlgorithm",
    "LeakyBucketAlgorithm",
    "get_algorithm",
    # -- Quotas ---------------------------------------------------------------------------------
    "QuotaManager",
    "QuotaRule",
    "QuotaKind",
    "QuotaPeriod",
    "QuotaUsage",
    "QuotaDecision",
    # -- CORS -----------------------------------------------------------------------------------
    "CorsPolicy",
    # -- Versionado -----------------------------------------------------------------------------
    "ApiVersion",
    "ApiVersioningPolicy",
    "ApiVersionNegotiator",
    "VersioningStrategy",
    "VersionNegotiation",
    # -- Validación de peticiones ---------------------------------------------------------------
    "RequestValidator",
    "RequestValidationPolicy",
    # -- Compresión -----------------------------------------------------------------------------
    "CompressionProvider",
    "GzipCompressionProvider",
    "BrotliCompressionProvider",
    "CompressionNegotiator",
    "CompressionPolicy",
    "CompressionAlgorithm",
    "parse_accept_encoding",
    # -- Idempotencia ---------------------------------------------------------------------------
    "IdempotencyManager",
    "IdempotencyRecord",
    "DEFAULT_IDEMPOTENT_METHODS",
    "build_fingerprint",
    # -- Auditoría de API -----------------------------------------------------------------------
    "ApiAudit",
    "ApiAuditRecord",
    "ApiOutcome",
    "build_audit_record",
    # -- Contratos de almacenamiento y sus implementaciones -------------------------------------
    "RateLimitStore",
    "QuotaStore",
    "IdempotencyStore",
    "AuditSink",
    "ApiProtectionPolicy",
    "InMemoryRateLimitStore",
    "InMemoryQuotaStore",
    "InMemoryIdempotencyStore",
    "InMemoryAuditSink",
    "LoggingAuditSink",
    "RedisRateLimitStore",
    "RedisQuotaStore",
    "RedisIdempotencyStore",
    # -- Middlewares ASGI (``ApiGateway.install`` los monta en el orden correcto) ---------------
    "RateLimitMiddleware",
    "QuotaMiddleware",
    "CorsMiddleware",
    "ApiVersionMiddleware",
    "RequestValidationMiddleware",
    "CompressionMiddleware",
    "IdempotencyMiddleware",
    "ApiAuditMiddleware",
    # -- Excepciones (todas RFC 7807 vía el manejador central del framework) --------------------
    "ApiProtectionException",
    "RateLimitExceededException",
    "QuotaExceededException",
    "RequestTooLargeException",
    "ResponseTooLargeException",
    "UnsupportedContentTypeException",
    "InvalidRequestException",
    "UnsupportedApiVersionException",
    "IdempotencyConflictException",
]
