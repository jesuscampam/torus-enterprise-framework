"""``ApiGateway`` — punto único de composición de la protección de APIs (Sprint 2.9).

Existe para que proteger una API sea *una* llamada (``gateway.install(app)``)
en vez de ocho ``add_middleware`` en el orden correcto. El orden importa
mucho y no es evidente, así que el framework lo fija una vez, aquí, y lo
justifica pieza por pieza (ver ``MIDDLEWARE_ORDER``).

``ApiGateway`` acepta cada subsistema por separado y todos son opcionales:
una aplicación que solo quiera CORS y rate limiting construye el gateway con
esos dos y no paga el coste de los demás — ningún middleware se instala si su
subsistema no está presente.

Además de instalar middlewares, expone ``evaluate()``: la misma cadena de
decisión (limitación + cuotas) aplicable a un ``ApiRequestContext`` fuera de
HTTP — desde un worker, un consumidor de cola o una prueba— sin levantar un
servidor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from teaf._internal.api.audit.audit import ApiAudit
from teaf._internal.api.compression.providers import CompressionNegotiator
from teaf._internal.api.cors.policy import CorsPolicy
from teaf._internal.api.idempotency.manager import IdempotencyManager
from teaf._internal.api.middleware.audit import ApiAuditMiddleware
from teaf._internal.api.middleware.compression import CompressionMiddleware
from teaf._internal.api.middleware.context import TrustedProxies
from teaf._internal.api.middleware.cors import CorsMiddleware
from teaf._internal.api.middleware.idempotency import IdempotencyMiddleware
from teaf._internal.api.middleware.quota import QuotaMiddleware, quota_headers
from teaf._internal.api.middleware.rate_limit import RateLimitMiddleware, rate_limit_headers
from teaf._internal.api.middleware.validation import RequestValidationMiddleware
from teaf._internal.api.middleware.versioning import ApiVersionMiddleware
from teaf._internal.api.models import ApiRequestContext, QuotaDecision, RateLimitDecision
from teaf._internal.api.quotas.manager import QuotaManager
from teaf._internal.api.ratelimit.limiter import RateLimiter
from teaf._internal.api.validation.validator import RequestValidator
from teaf._internal.api.versioning.negotiator import ApiVersionNegotiator
from teaf._internal.core.logging import get_logger
from teaf._internal.runtime.event_bus import EventBus

#: Orden de **ejecución** de la cadena, del más externo al más interno.
#: Starlette ejecuta los middlewares en orden inverso al de registro, así
#: que ``install()`` los añade recorriendo esta tupla al revés.
#:
#: - ``cors`` primero: sus cabeceras deben acompañar también a los errores
#:   (un 429 sin ellas es invisible para el navegador, ver ``middleware/cors.py``).
#: - ``audit`` inmediatamente después: así audita todo lo que pase por dentro,
#:   incluidos los rechazos de las capas siguientes.
#: - ``compression`` antes que el resto de la lógica: comprime la respuesta
#:   final, ya construida.
#: - ``versioning`` antes que ``validation``: la versión puede condicionar qué
#:   se considera válido.
#: - ``rate_limit`` antes que ``quota``: el límite protege la disponibilidad
#:   inmediata y es más barato de evaluar; no tiene sentido gastar una cuota
#:   contratada en una petición que va a rechazarse igualmente.
#: - ``idempotency`` al final: guarda la respuesta tal y como la produjo el
#:   endpoint, sin comprimir y sin cabeceras de capas exteriores.
MIDDLEWARE_ORDER: tuple[str, ...] = (
    "cors",
    "audit",
    "compression",
    "versioning",
    "validation",
    "rate_limit",
    "quota",
    "idempotency",
)


class _SupportsAddMiddleware(Protocol):
    """Lo único que ``install()`` necesita de una aplicación: ``add_middleware``."""

    def add_middleware(self, middleware_class: type, /, **options: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class GatewayDecision:
    """Resultado de evaluar la cadena de protección sobre un ``ApiRequestContext``.

    ``headers`` trae ya las cabeceras informativas (``X-RateLimit-*``,
    ``X-Quota-*``, ``Retry-After``) que correspondería devolver al cliente,
    para que quien use ``evaluate()`` fuera de HTTP no tenga que derivarlas.
    """

    allowed: bool
    reason: str | None = None
    rate_limit: RateLimitDecision | None = None
    quota: QuotaDecision | None = None
    retry_after_seconds: float = 0.0
    headers: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "rateLimit": self.rate_limit.as_dict() if self.rate_limit else None,
            "quota": self.quota.as_dict() if self.quota else None,
            "retryAfterSeconds": round(self.retry_after_seconds, 3),
            "headers": dict(self.headers),
        }


class ApiGateway:
    """Compone rate limiting, quotas, CORS, versionado, validación, compresión,
    idempotencia y auditoría en una única cadena de protección."""

    def __init__(
        self,
        *,
        rate_limiter: RateLimiter | None = None,
        quota_manager: QuotaManager | None = None,
        cors: CorsPolicy | None = None,
        versioning: ApiVersionNegotiator | None = None,
        validator: RequestValidator | None = None,
        compression: CompressionNegotiator | None = None,
        idempotency: IdempotencyManager | None = None,
        audit: ApiAudit | None = None,
        event_bus: EventBus | None = None,
        trust_forwarded_headers: bool = True,
        trusted_proxies: TrustedProxies | Sequence[str] | None = None,
        validate_responses: bool = False,
    ) -> None:
        self.rate_limiter = rate_limiter
        self.quota_manager = quota_manager
        self.cors = cors
        self.versioning = versioning
        self.validator = validator
        self.compression = compression
        self.idempotency = idempotency
        self.audit = audit
        self.event_bus = event_bus
        self.trust_forwarded_headers = trust_forwarded_headers
        #: Se compila una sola vez aquí, no por petición (ver ``TrustedProxies``).
        #: Acepta también una secuencia de cadenas por comodidad de quien
        #: construya el gateway a mano.
        self.trusted_proxies = (
            trusted_proxies
            if isinstance(trusted_proxies, TrustedProxies)
            else TrustedProxies.parse(trusted_proxies or ())
        )
        self.validate_responses = validate_responses

    def _middleware_specs(self) -> dict[str, tuple[type, dict[str, Any]]]:
        """Clase y argumentos de cada middleware cuyo subsistema está configurado."""
        specs: dict[str, tuple[type, dict[str, Any]]] = {}

        if self.cors is not None and self.cors.enabled:
            specs["cors"] = (CorsMiddleware, {"policy": self.cors})
        if self.audit is not None:
            specs["audit"] = (
                ApiAuditMiddleware,
                {
                    "audit": self.audit,
                    "trust_forwarded_headers": self.trust_forwarded_headers,
                    "trusted_proxies": self.trusted_proxies,
                },
            )
        if self.compression is not None:
            specs["compression"] = (CompressionMiddleware, {"negotiator": self.compression})
        if self.versioning is not None:
            specs["versioning"] = (ApiVersionMiddleware, {"negotiator": self.versioning})
        if self.validator is not None:
            specs["validation"] = (
                RequestValidationMiddleware,
                {"validator": self.validator, "validate_responses": self.validate_responses},
            )
        if self.rate_limiter is not None:
            specs["rate_limit"] = (
                RateLimitMiddleware,
                {
                    "limiter": self.rate_limiter,
                    "trust_forwarded_headers": self.trust_forwarded_headers,
                    "trusted_proxies": self.trusted_proxies,
                },
            )
        if self.quota_manager is not None:
            specs["quota"] = (
                QuotaMiddleware,
                {
                    "manager": self.quota_manager,
                    "trust_forwarded_headers": self.trust_forwarded_headers,
                    "trusted_proxies": self.trusted_proxies,
                },
            )
        if self.idempotency is not None:
            specs["idempotency"] = (IdempotencyMiddleware, {"manager": self.idempotency})
        return specs

    @property
    def enabled_middlewares(self) -> tuple[str, ...]:
        """Nombres de los middlewares que ``install()`` añadiría, en orden de ejecución."""
        specs = self._middleware_specs()
        return tuple(name for name in MIDDLEWARE_ORDER if name in specs)

    def install(self, app: _SupportsAddMiddleware) -> tuple[str, ...]:
        """Añade a ``app`` los middlewares de los subsistemas configurados.

        ``app`` es cualquier aplicación con ``add_middleware`` (``FastAPI`` o
        ``Starlette``). Debe llamarse **antes** de que arranque el ciclo de
        vida ASGI: Starlette congela su pila de middlewares en el primer
        arranque y añadir uno después no tiene efecto.

        Nota sobre el orden respecto a los middlewares propios del framework
        (``RequestIdMiddleware``/``RequestLoggingMiddleware``, añadidos por
        ``create_app``): al instalarse después, estos quedan **por fuera** de
        ellos. Es lo correcto para CORS y auditoría (deben ver también lo que
        el framework rechace), y el correlation-id sigue disponible porque
        ``build_request_context`` cae a la cabecera entrante cuando el
        ``ContextVar`` aún no está fijado (ver ``middleware/context.py``).

        Returns:
            Los nombres de los middlewares instalados, en orden de ejecución.
        """
        specs = self._middleware_specs()
        installed = tuple(name for name in MIDDLEWARE_ORDER if name in specs)
        self._warn_if_forwarded_headers_are_trusted(installed)
        # Se registran del más interno al más externo porque Starlette ejecuta
        # los middlewares en orden inverso al de registro.
        for name in reversed(installed):
            middleware_class, options = specs[name]
            # Se pasa un proveedor, no el bus: ``install()`` corre antes de
            # que arranque el ciclo de vida ASGI, y el ``EventBus`` del
            # Runtime todavía no existe en ese momento (ver el docstring
            # de ``ApiProtectionMiddleware.__init__``).
            app.add_middleware(
                middleware_class, event_bus_provider=lambda: self.event_bus, **options
            )
        return installed

    def _warn_if_forwarded_headers_are_trusted(self, installed: tuple[str, ...]) -> None:
        """Avisa una vez si se va a confiar en cabeceras que el cliente controla.

        ``X-Forwarded-For`` la falsifica cualquier cliente. Detrás de un proxy
        que la **reescriba**, confiar en ella es correcto y necesario —sin eso,
        todo el tráfico compartiría la IP del balanceador y cualquier límite
        por IP se volvería global—. Expuesta directamente a internet, en
        cambio, basta con enviar una IP distinta en cada petición para saltarse
        el limitador entero.

        El framework no puede distinguir los dos despliegues, así que no
        cambia el valor por defecto —hacerlo rompería silenciosamente a quien
        hoy está bien desplegado, que es el caso mayoritario— pero **tampoco
        acepta el riesgo en silencio**: lo dice al arrancar, una sola vez, y
        solo cuando hay algún middleware que realmente usa la IP del cliente.
        Ver ADR-010 y docs/SECURITY-REVIEW.md (H-2).

        Desde Sprint 3.0 (ADR-011) el aviso **desaparece en cuanto se
        configura ``trusted_proxies``**: ahí ya no se confía a ciegas sino
        solo en proxies conocidos, que es justo lo que el aviso pedía
        resolver. Seguir avisando entonces sería ruido, y el ruido es lo que
        acaba haciendo que nadie lea los avisos.
        """
        if self.trusted_proxies or not self.trust_forwarded_headers:
            return
        afectados = tuple(name for name in ("rate_limit", "quota", "audit") if name in installed)
        if not afectados:
            return
        get_logger("teaf.api.gateway").warning(
            "forwarded_headers_trusted",
            extra={
                "context": {
                    "middlewares": list(afectados),
                    "riesgo": (
                        "La IP del cliente se toma de X-Forwarded-For/X-Real-IP, que el "
                        "cliente puede falsificar. Correcto detrás de un proxy que las "
                        "reescriba; inseguro si la aplicación está expuesta directamente "
                        "a internet."
                    ),
                    "accion": (
                        "Si no hay un proxy de confianza delante, configure "
                        "trust_forwarded_headers=False (API_TRUST_FORWARDED_HEADERS=false)."
                    ),
                }
            },
        )

    async def evaluate(self, context: ApiRequestContext) -> GatewayDecision:
        """Aplica limitación y cuotas a ``context``, sin pasar por HTTP.

        Consume cuota igual que lo haría una petición real — es la misma
        llamada que hacen los middlewares. Para consultar el estado sin
        consumir, ver ``RateLimiter.inspect``/``QuotaManager.usage``.
        """
        if self.rate_limiter is not None:
            denial = await self.rate_limiter.acquire(context)
            if denial is not None:
                return GatewayDecision(
                    allowed=False,
                    reason="rate-limit-exceeded",
                    rate_limit=denial,
                    retry_after_seconds=denial.retry_after_seconds,
                    headers=rate_limit_headers(denial),
                )

        if self.quota_manager is not None:
            quota_denial = await self.quota_manager.consume(context)
            if quota_denial is not None:
                return GatewayDecision(
                    allowed=False,
                    reason="quota-exceeded",
                    quota=quota_denial,
                    retry_after_seconds=quota_denial.retry_after_seconds,
                    headers=quota_headers(quota_denial),
                )

        return GatewayDecision(allowed=True)

    async def release(self, context: ApiRequestContext) -> None:
        """Libera las cuotas de concurrencia tomadas por ``evaluate()``.

        Simétrica de ``evaluate()``: quien la use fuera de HTTP debe llamarla
        en un ``finally``, igual que hace ``QuotaMiddleware``.
        """
        if self.quota_manager is not None:
            await self.quota_manager.release(context)

    def describe(self) -> dict[str, object]:
        """Resumen inspeccionable de la protección configurada.

        Lo consumen el manifiesto del módulo y el diagnóstico del Runtime —
        poder responder "¿qué protege exactamente esta API?" sin leer código
        es parte de lo que hace gobernable una plataforma.
        """
        return {
            "middlewares": list(self.enabled_middlewares),
            "rateLimitRules": (
                [rule.name for rule in self.rate_limiter.rules] if self.rate_limiter else []
            ),
            "quotaRules": (
                [rule.name for rule in self.quota_manager.rules] if self.quota_manager else []
            ),
            "corsEnabled": self.cors is not None and self.cors.enabled,
            "supportedVersions": (
                [str(v) for v in self.versioning.policy.supported] if self.versioning else []
            ),
            "compressionAlgorithms": (
                [p.algorithm.value for p in self.compression.providers] if self.compression else []
            ),
            "idempotencyEnabled": self.idempotency is not None and self.idempotency.enabled,
            "auditSinks": [sink.name for sink in self.audit.sinks] if self.audit else [],
        }
