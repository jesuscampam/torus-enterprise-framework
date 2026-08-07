"""``build_api_protection_manifest`` — el ``ModuleManifest`` del API Protection Module.

Separado de ``ApiProtectionModule`` (``module.py``) a propósito, mismo
criterio que ``modules/security/manifest.py`` y
``modules/observability/manifest.py``: aquí solo se *describe* el módulo —
nada se registra contra ningún ``Runtime`` desde este archivo, eso lo hace
el SDK durante ``ModuleBase.bootstrap()``.

Los seis servicios declarados son exactamente los que el Sprint 2.9 exige
registrar automáticamente en el contenedor de dependencias
(``RateLimiter``, ``QuotaManager``, ``ApiAudit``, ``CompressionProvider``,
``RequestValidator``, ``IdempotencyManager``), más ``ApiGateway`` como
séptimo: sin él, resolver los seis por separado obligaría a recomponer a
mano la cadena que el gateway ya tiene montada.
"""

from __future__ import annotations

from teaf._internal.api.audit.audit import ApiAudit
from teaf._internal.api.gateway.gateway import ApiGateway
from teaf._internal.api.idempotency.manager import IdempotencyManager
from teaf._internal.api.module.configuration import ApiProtectionConfiguration
from teaf._internal.api.module.health import ApiProtectionHealth
from teaf._internal.api.quotas.manager import QuotaManager
from teaf._internal.api.ratelimit.limiter import RateLimiter
from teaf._internal.api.validation.validator import RequestValidator
from teaf._internal.contracts.api import CompressionProvider
from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.manifest import ModuleManifest

#: Los ocho eventos que la plataforma publica en el ``EventBus`` del Runtime.
#: Declararlos en el manifiesto es lo que permite descubrirlos vía
#: ``GET /runtime/modules`` sin leer el código de los middlewares.
API_PROTECTION_EVENTS: tuple[str, ...] = (
    "request.accepted",
    "request.rejected",
    "rate.limit.exceeded",
    "quota.exceeded",
    "idempotency.detected",
    "request.compressed",
    "audit.recorded",
    "version.negotiated",
)


def build_api_protection_manifest(
    configuration: ApiProtectionConfiguration,
    *,
    gateway: ApiGateway,
    health: ApiProtectionHealth,
) -> ModuleManifest:
    """Construye el manifiesto del API Protection Module sobre instancias ya construidas.

    ``gateway``/``health`` se construyen en ``ApiProtectionModule.__init__``
    (antes de que ``bootstrap()`` llame a ``get_manifest()`` por primera vez)
    — este builder solo los declara, nunca los crea.
    """
    builder = (
        ModuleBuilder(id="api-protection", name="api-protection", display_name="API Protection")
        .with_version("1.0.0")
        .with_description(
            "Plataforma empresarial de protección y gobernanza de APIs de TEAF: rate limiting, "
            "quotas, CORS, versionado, validación de peticiones, compresión, idempotencia y "
            "auditoría."
        )
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.API)
        .with_tags(
            "api",
            "rate-limiting",
            "quotas",
            "cors",
            "versioning",
            "validation",
            "compression",
            "idempotency",
            "audit",
        )
        .with_documentation("docs/api/API-PROTECTION.md")
        .with_runtime_compatibility(">=0.6.0")
        .with_sdk_compatibility(">=1.0.0")
        .add_capability(
            id="api.protection",
            name="api-protection",
            category=CapabilityCategory.API,
            description="Protección y gobernanza de APIs — capacidad general del módulo.",
        )
        .add_capability(
            id="api.rate-limit",
            name="api-rate-limit",
            category=CapabilityCategory.API,
            description="Limitación de peticiones (ventana fija/deslizante, token/leaky bucket).",
        )
        .add_capability(
            id="api.quota",
            name="api-quota",
            category=CapabilityCategory.API,
            description="Cuotas de consumo por período, ancho de banda, payload y concurrencia.",
        )
        .add_capability(
            id="api.cors",
            name="api-cors",
            category=CapabilityCategory.API,
            description="Política CORS configurable, con comodines de subdominio.",
        )
        .add_capability(
            id="api.versioning",
            name="api-versioning",
            category=CapabilityCategory.API,
            description="Versionado por URI, cabecera o tipo de medio, con deprecación.",
        )
        .add_capability(
            id="api.validation",
            name="api-validation",
            category=CapabilityCategory.API,
            description="Validación de borde: tamaño, tipo de contenido, cabeceras y agente.",
        )
        .add_capability(
            id="api.compression",
            name="api-compression",
            category=CapabilityCategory.API,
            description="Compresión de respuestas (GZip y Brotli) con umbral mínimo.",
        )
        .add_capability(
            id="api.idempotency",
            name="api-idempotency",
            category=CapabilityCategory.API,
            description="Idempotencia por clave de cliente, con detección de reintentos.",
        )
        .add_capability(
            id="api.audit",
            name="api-audit",
            category=CapabilityCategory.API,
            description="Auditoría completa de peticiones, integrada con Observability.",
        )
        .add_configuration(
            key="rate_limit_enabled",
            description="Activa la limitación de peticiones.",
            default=configuration.rate_limit_enabled,
        )
        .add_configuration(
            key="rate_limit_requests",
            description="Peticiones permitidas por ventana en la regla por defecto.",
            default=configuration.rate_limit_requests,
        )
        .add_configuration(
            key="rate_limit_algorithm",
            description=(
                "Algoritmo de limitación: fixed_window, sliding_window, token_bucket "
                "o leaky_bucket."
            ),
            default=configuration.rate_limit_algorithm,
        )
        .add_configuration(
            key="quotas_enabled",
            description="Activa las cuotas de consumo por período.",
            default=configuration.quotas_enabled,
        )
        .add_configuration(
            key="cors_allow_origins",
            description="Orígenes permitidos por CORS (vacío = CORS desactivado).",
            default=list(configuration.cors_allow_origins),
        )
        .add_configuration(
            key="versioning_supported",
            description="Versiones de API servidas.",
            default=list(configuration.versioning_supported),
        )
        .add_configuration(
            key="compression_enabled",
            description="Activa la compresión de respuestas.",
            default=configuration.compression_enabled,
        )
        .add_configuration(
            key="idempotency_enabled",
            description="Activa la idempotencia gestionada por 'Idempotency-Key'.",
            default=configuration.idempotency_enabled,
        )
        .add_configuration(
            key="audit_enabled",
            description="Activa la auditoría de peticiones.",
            default=configuration.audit_enabled,
        )
        .add_service(
            ApiGateway,
            lambda c: gateway,
            lifetime=Lifetime.SINGLETON,
            description="Cadena completa de protección de APIs, ya compuesta.",
            capabilities=("api.protection",),
        )
        .add_healthcheck(
            name="api.protection.ping",
            description="Al menos una protección activa en la cadena del gateway.",
            check=health.check,
        )
    )

    # Los seis servicios exigidos por el Sprint se registran solo si su
    # subsistema está construido: registrar un ``RateLimiter`` inexistente
    # haría que ``runtime.resolve(RateLimiter)`` devolviera ``None`` en vez
    # de fallar de forma clara.
    if gateway.rate_limiter is not None:
        limiter = gateway.rate_limiter
        builder.add_service(
            RateLimiter,
            lambda c: limiter,
            lifetime=Lifetime.SINGLETON,
            description="Limitador de peticiones con las reglas configuradas.",
            capabilities=("api.rate-limit",),
        )
    if gateway.quota_manager is not None:
        quotas = gateway.quota_manager
        builder.add_service(
            QuotaManager,
            lambda c: quotas,
            lifetime=Lifetime.SINGLETON,
            description="Gestor de cuotas de consumo.",
            capabilities=("api.quota",),
        )
    if gateway.audit is not None:
        audit = gateway.audit
        builder.add_service(
            ApiAudit,
            lambda c: audit,
            lifetime=Lifetime.SINGLETON,
            description="Auditoría de API, con sus destinos configurados.",
            capabilities=("api.audit",),
        )
    if gateway.validator is not None:
        validator = gateway.validator
        builder.add_service(
            RequestValidator,
            lambda c: validator,
            lifetime=Lifetime.SINGLETON,
            description="Validador de borde de peticiones y respuestas.",
            capabilities=("api.validation",),
        )
    if gateway.idempotency is not None:
        idempotency = gateway.idempotency
        builder.add_service(
            IdempotencyManager,
            lambda c: idempotency,
            lifetime=Lifetime.SINGLETON,
            description="Gestor de idempotencia por 'Idempotency-Key'.",
            capabilities=("api.idempotency",),
        )
    if gateway.compression is not None and gateway.compression.providers:
        # Se registra el proveedor preferido del servidor bajo el contrato
        # ``CompressionProvider``; el negociador completo viaja dentro del
        # ``ApiGateway``, que también está en el contenedor.
        preferred = gateway.compression.providers[0]
        builder.add_service(
            CompressionProvider,
            lambda c: preferred,
            lifetime=Lifetime.SINGLETON,
            description="Proveedor de compresión preferido del servidor.",
            capabilities=("api.compression",),
        )

    for event in API_PROTECTION_EVENTS:
        builder.add_event(event)

    return builder.build()
