"""Modelo de dominio de la plataforma de protección de APIs (Sprint 2.9, ADR-009).

Todo el vocabulario compartido por los ocho subsistemas de protección
(rate limiting, quotas, CORS, versionado, validación, compresión,
idempotencia y auditoría) vive aquí, en un único archivo, por la misma
razón que ``observability/models.py``: son tipos de datos puros, sin
comportamiento de infraestructura, y repartirlos por subcarpeta obligaría
a cada subsistema a importar a los demás solo para tipar sus firmas.

``ApiRequestContext`` es la pieza central: la descripción neutral de "quién
hace esta petición y sobre qué" que consumen rate limiting, quotas y
auditoría por igual. Es deliberadamente independiente de Starlette/FastAPI
(no contiene un ``Request``) para que toda la plataforma sea testeable —y
reutilizable desde un worker, un job o un gateway externo— sin levantar un
servidor HTTP; los middlewares (``api/middleware/``) son los únicos que
traducen una petición ASGI real a este contexto.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

# ---------------------------------------------------------------------------
# Contexto de petición — el vocabulario común de toda la plataforma
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApiRequestContext:
    """Quién realiza una petición y sobre qué recurso — sin acoplarse a HTTP.

    Los campos de identidad (``user_id``/``api_key_id``/``tenant_id``/
    ``roles``) los rellena ``build_request_context`` a partir del
    ``SecurityContext`` ya resuelto por ``SecurityMiddleware`` (Sprint 2.7);
    la plataforma de protección nunca autentica por su cuenta — solo
    *consume* la identidad que Security ya estableció.
    """

    method: str = "GET"
    path: str = "/"
    client_ip: str | None = None
    user_id: str | None = None
    api_key_id: str | None = None
    tenant_id: str | None = None
    roles: tuple[str, ...] = ()
    #: Tamaño declarado del cuerpo de la petición (``Content-Length``), en bytes.
    request_bytes: int = 0
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    user_agent: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "path": self.path,
            "clientIp": self.client_ip,
            "userId": self.user_id,
            "apiKeyId": self.api_key_id,
            "tenantId": self.tenant_id,
            "roles": list(self.roles),
            "requestBytes": self.request_bytes,
            "correlationId": self.correlation_id,
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "userAgent": self.user_agent,
        }


class ProtectionScope(str, Enum):
    """Por qué dimensión se agrupa el consumo de una regla de protección.

    Compartido por rate limiting y quotas — ambos necesitan exactamente el
    mismo juego de dimensiones, así que no se duplica el enum (DRY).
    """

    GLOBAL = "global"
    USER = "user"
    API_KEY = "api_key"
    TENANT = "tenant"
    IP = "ip"
    ENDPOINT = "endpoint"
    ROLE = "role"


def resolve_scope_key(scope: ProtectionScope, context: ApiRequestContext) -> str:
    """Deriva la clave de agrupación de ``context`` para ``scope``.

    Cuando la dimensión no está presente en la petición (p. ej. ``USER`` en
    una petición anónima) devuelve ``"anonymous"`` en vez de ``None``: una
    regla por usuario debe seguir limitando el tráfico sin identificar, no
    dejarlo pasar sin control.
    """
    if scope is ProtectionScope.GLOBAL:
        return "global"
    if scope is ProtectionScope.USER:
        return context.user_id or "anonymous"
    if scope is ProtectionScope.API_KEY:
        return context.api_key_id or "anonymous"
    if scope is ProtectionScope.TENANT:
        return context.tenant_id or "default"
    if scope is ProtectionScope.IP:
        return context.client_ip or "unknown"
    if scope is ProtectionScope.ENDPOINT:
        return f"{context.method} {context.path}"
    # ProtectionScope.ROLE — el primer rol ordenado alfabéticamente, para que
    # la clave sea estable aunque el resolutor devuelva los roles en otro orden.
    return sorted(context.roles)[0] if context.roles else "anonymous"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class RateLimitAlgorithm(str, Enum):
    """Los cuatro algoritmos de limitación implementados (ver ADR-009)."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    """Una regla de limitación: cuántas peticiones, en cuánto tiempo y por qué dimensión.

    ``burst`` solo lo usan ``TOKEN_BUCKET`` (capacidad del cubo) y
    ``LEAKY_BUCKET`` (profundidad de la cola); cuando es ``None`` ambos usan
    ``limit`` como capacidad, que es el comportamiento sin ráfaga extra.

    ``endpoints``/``roles``, si no están vacíos, restringen a qué peticiones
    aplica la regla (``endpoints`` admite el comodín final ``*``, p. ej.
    ``"/api/v1/orders*"``).
    """

    name: str
    limit: int
    window_seconds: float
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW
    scope: ProtectionScope = ProtectionScope.IP
    burst: int | None = None
    endpoints: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()

    @property
    def capacity(self) -> int:
        """Capacidad efectiva del cubo (token/leaky bucket)."""
        return self.burst if self.burst is not None else self.limit

    @property
    def refill_rate(self) -> float:
        """Unidades reabastecidas (token bucket) o drenadas (leaky) por segundo."""
        return self.limit / self.window_seconds if self.window_seconds > 0 else float(self.limit)

    def matches(self, context: ApiRequestContext) -> bool:
        """``True`` si esta regla aplica a ``context`` (endpoint y rol)."""
        if self.endpoints and not any(_path_matches(p, context.path) for p in self.endpoints):
            return False
        if self.roles and not set(self.roles) & set(context.roles):
            return False
        return True


def _path_matches(pattern: str, path: str) -> bool:
    """Coincidencia de ruta: igualdad exacta, o prefijo cuando ``pattern`` acaba en ``*``."""
    if pattern.endswith("*"):
        return path.startswith(pattern[:-1])
    return pattern == path


@dataclass(frozen=True, slots=True)
class RateLimitState:
    """Estado persistido por clave — cada algoritmo interpreta los campos que necesita.

    Un único tipo de estado (en vez de uno por algoritmo) mantiene el
    contrato ``RateLimitStore`` con una sola forma serializable, que es lo
    que permite que un backend Redis lo guarde como un hash plano sin
    conocer qué algoritmo lo produjo (ver ADR-009).
    """

    #: ``TOKEN_BUCKET``: tokens disponibles. ``LEAKY_BUCKET``: nivel del cubo.
    tokens: float = 0.0
    #: Marca de tiempo del último cálculo (token/leaky bucket).
    updated_at: float = 0.0
    #: ``FIXED_WINDOW``: peticiones contadas en la ventana actual.
    count: int = 0
    #: ``FIXED_WINDOW``: instante de inicio de la ventana actual.
    window_start: float = 0.0
    #: ``SLIDING_WINDOW``: marcas de tiempo de las peticiones aún dentro de la ventana.
    timestamps: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Resultado de evaluar una petición contra una regla de limitación.

    ``remaining``/``reset_after_seconds`` alimentan las cabeceras estándar
    ``X-RateLimit-*``; ``retry_after_seconds`` alimenta ``Retry-After``
    cuando la petición se rechaza (ver docs/api/RATE-LIMITING.md).
    """

    allowed: bool
    rule: str
    key: str
    limit: int
    remaining: int
    reset_after_seconds: float
    retry_after_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "rule": self.rule,
            "key": self.key,
            "limit": self.limit,
            "remaining": self.remaining,
            "resetAfterSeconds": round(self.reset_after_seconds, 3),
            "retryAfterSeconds": round(self.retry_after_seconds, 3),
        }


# ---------------------------------------------------------------------------
# Quotas
# ---------------------------------------------------------------------------


class QuotaPeriod(str, Enum):
    """Ventana de acumulación de una cuota."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


#: Duración en segundos de cada período. El mes se aproxima a 30 días — una
#: cuota mensual es un límite comercial, no un calendario contable, y usar
#: 30 días mantiene la aritmética de ventanas idéntica al resto de períodos
#: (ver docs/api/QUOTAS.md, "Por qué el mes son 30 días").
_PERIOD_SECONDS: dict[QuotaPeriod, float] = {
    QuotaPeriod.MINUTE: 60.0,
    QuotaPeriod.HOUR: 3_600.0,
    QuotaPeriod.DAY: 86_400.0,
    QuotaPeriod.MONTH: 2_592_000.0,
}


def period_seconds(period: QuotaPeriod) -> float:
    """Duración, en segundos, de ``period``."""
    return _PERIOD_SECONDS[period]


class QuotaKind(str, Enum):
    """Qué magnitud consume una cuota."""

    REQUESTS = "requests"
    BANDWIDTH = "bandwidth"
    PAYLOAD = "payload"
    CONCURRENT = "concurrent"


@dataclass(frozen=True, slots=True)
class QuotaRule:
    """Una cuota: cuánta magnitud (``kind``) se permite por período y dimensión.

    ``CONCURRENT`` es la única que no acumula por período sino que mide
    peticiones simultáneas — se incrementa al entrar y se decrementa al
    salir (``QuotaManager.release``), por lo que su ``period`` se ignora.

    ``PAYLOAD`` tampoco acumula: limita el tamaño de *una* petición
    individual, así que se evalúa comparando ``amount`` contra ``limit``
    sin tocar el almacén.
    """

    name: str
    kind: QuotaKind = QuotaKind.REQUESTS
    limit: int = 1_000
    period: QuotaPeriod = QuotaPeriod.DAY
    scope: ProtectionScope = ProtectionScope.TENANT

    @property
    def accumulates(self) -> bool:
        """``True`` si la cuota suma consumo a lo largo de una ventana temporal."""
        return self.kind in (QuotaKind.REQUESTS, QuotaKind.BANDWIDTH)


@dataclass(frozen=True, slots=True)
class QuotaUsage:
    """Consumo actual de una cuota concreta para una clave concreta."""

    rule: str
    kind: QuotaKind
    key: str
    consumed: float
    limit: int
    period: QuotaPeriod

    @property
    def remaining(self) -> float:
        """Magnitud aún disponible (nunca negativa)."""
        return max(0.0, self.limit - self.consumed)

    def as_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "kind": self.kind.value,
            "key": self.key,
            "consumed": self.consumed,
            "limit": self.limit,
            "remaining": self.remaining,
            "period": self.period.value,
        }


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    """Resultado de intentar consumir una cuota."""

    allowed: bool
    usage: QuotaUsage
    retry_after_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "usage": self.usage.as_dict(),
            "retryAfterSeconds": round(self.retry_after_seconds, 3),
        }


# ---------------------------------------------------------------------------
# Versionado de API
# ---------------------------------------------------------------------------


class VersioningStrategy(str, Enum):
    """Dónde viaja la versión solicitada por el cliente."""

    URI = "uri"
    HEADER = "header"
    MEDIA_TYPE = "media_type"


@dataclass(frozen=True, order=True, slots=True)
class ApiVersion:
    """Una versión de API, comparable y ordenable (``ApiVersion(1) < ApiVersion(2)``).

    ``order=True`` sobre ``(major, minor)`` es lo que hace posible la
    negociación "la versión soportada más alta que no exceda la pedida"
    sin escribir comparaciones a mano.
    """

    major: int
    minor: int = 0

    @classmethod
    def parse(cls, value: str) -> ApiVersion:
        """Interpreta ``"v1"``, ``"1"``, ``"v2.1"`` o ``"2.1"`` como ``ApiVersion``.

        Raises:
            ValueError: si ``value`` no tiene una forma reconocible.
        """
        cleaned = value.strip().lower().lstrip("v")
        if not cleaned:
            raise ValueError(f"Versión de API vacía: {value!r}")
        parts = cleaned.split(".")
        if len(parts) > 2 or not all(part.isdigit() for part in parts):
            raise ValueError(f"Versión de API no reconocida: {value!r}")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) == 2 else 0
        return cls(major=major, minor=minor)

    def __str__(self) -> str:
        """``"v1"`` cuando ``minor`` es 0, ``"v1.2"`` en otro caso."""
        return f"v{self.major}" if self.minor == 0 else f"v{self.major}.{self.minor}"


@dataclass(frozen=True, slots=True)
class VersionNegotiation:
    """Qué versión se resolvió para una petición, y cómo.

    ``requested`` es ``None`` cuando el cliente no pidió ninguna versión y se
    aplicó la de por defecto (``is_default`` a ``True``).
    """

    version: ApiVersion
    strategy: VersioningStrategy | None
    requested: str | None = None
    is_default: bool = False
    deprecated: bool = False
    sunset: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "version": str(self.version),
            "strategy": self.strategy.value if self.strategy else None,
            "requested": self.requested,
            "isDefault": self.is_default,
            "deprecated": self.deprecated,
            "sunset": self.sunset,
        }


# ---------------------------------------------------------------------------
# Compresión
# ---------------------------------------------------------------------------


class CompressionAlgorithm(str, Enum):
    """Codificaciones de contenido soportadas — el valor es el token de ``Content-Encoding``."""

    GZIP = "gzip"
    BROTLI = "br"
    IDENTITY = "identity"


# ---------------------------------------------------------------------------
# Idempotencia
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """La respuesta ya emitida para una ``Idempotency-Key``, lista para reproducirse.

    ``fingerprint`` es el hash del cuerpo/ruta/método originales: reusar la
    misma clave con una petición distinta es un error del cliente
    (``IdempotencyConflictException``), no una reproducción válida.
    """

    key: str
    fingerprint: str
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)
    created_at: float = 0.0
    expires_at: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "fingerprint": self.fingerprint,
            "statusCode": self.status_code,
            "bodyBytes": len(self.body),
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
        }


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------


class ApiOutcome(str, Enum):
    """Cómo terminó una petición desde el punto de vista de la protección."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REPLAYED = "replayed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ApiAuditRecord:
    """Una entrada de auditoría de API — todo lo exigido por el Sprint 2.9, en un solo tipo.

    Incluye correlation/trace/span-id para poder cruzar cada entrada con las
    trazas y los logs producidos por la plataforma de observabilidad
    (Sprint 2.8) sin necesidad de una correlación externa.
    """

    method: str
    path: str
    status_code: int
    latency_seconds: float
    outcome: ApiOutcome = ApiOutcome.ACCEPTED
    identity_id: str | None = None
    tenant_id: str | None = None
    api_key_id: str | None = None
    client_ip: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    api_version: str | None = None
    request_bytes: int = 0
    response_bytes: int = 0
    reason: str | None = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "path": self.path,
            "statusCode": self.status_code,
            "latencySeconds": round(self.latency_seconds, 6),
            "outcome": self.outcome.value,
            "identityId": self.identity_id,
            "tenantId": self.tenant_id,
            "apiKeyId": self.api_key_id,
            "clientIp": self.client_ip,
            "correlationId": self.correlation_id,
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "apiVersion": self.api_version,
            "requestBytes": self.request_bytes,
            "responseBytes": self.response_bytes,
            "reason": self.reason,
            "recordedAt": self.recorded_at.isoformat(),
        }
