"""``build_observability_manifest`` — el ``ModuleManifest`` del Observability Module.

Separado de ``ObservabilityModule`` (``module.py``) a propósito, mismo
criterio que ``modules/security/manifest.py``: aquí solo se *describe* el
módulo — nada se registra contra ningún ``Runtime`` desde este archivo,
eso lo hace el SDK durante ``ModuleBase.bootstrap()``.
"""

from __future__ import annotations

from teaf._internal.contracts.telemetry import Meter, Tracer
from teaf._internal.modules.observability.configuration import ObservabilityConfiguration
from teaf._internal.modules.observability.health import ObservabilityHealth
from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.manifest import ModuleManifest


def build_observability_manifest(
    configuration: ObservabilityConfiguration,
    *,
    tracer: Tracer,
    meter: Meter,
    health: ObservabilityHealth,
) -> ModuleManifest:
    """Construye el manifiesto del Observability Module sobre instancias ya construidas.

    ``tracer``/``meter``/``health`` se construyen en
    ``ObservabilityModule.__init__`` (antes de que ``bootstrap()`` llame a
    ``get_manifest()`` por primera vez) — este builder solo los declara,
    nunca los crea.
    """
    return (
        ModuleBuilder(id="observability", name="observability", display_name="Observability")
        .with_version("1.0.0")
        .with_description(
            "Plataforma de observabilidad empresarial de TEAF: logging estructurado, "
            "trazas distribuidas, métricas, health checks y diagnósticos, sobre OpenTelemetry."
        )
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.OBSERVABILITY)
        .with_tags("observability", "opentelemetry", "tracing", "metrics", "logging", "health")
        .with_documentation("docs/observability/OBSERVABILITY.md")
        .with_runtime_compatibility(">=0.6.0")
        .with_sdk_compatibility(">=1.0.0")
        .add_capability(
            id="observability",
            name="observability",
            category=CapabilityCategory.OBSERVABILITY,
            description="Plataforma de observabilidad — capacidad general del módulo.",
        )
        .add_capability(
            id="observability.tracing",
            name="observability-tracing",
            category=CapabilityCategory.OBSERVABILITY,
            description="Tracing distribuido (spans, contexto, exportación) vía OpenTelemetry.",
        )
        .add_capability(
            id="observability.metrics",
            name="observability-metrics",
            category=CapabilityCategory.OBSERVABILITY,
            description="Métricas (contadores, histogramas, gauges) vía OpenTelemetry.",
        )
        .add_capability(
            id="observability.health",
            name="observability-health",
            category=CapabilityCategory.OBSERVABILITY,
            description="Health checks compuestos (liveness/readiness/startup/dependencias).",
        )
        .add_configuration(
            key="service_name",
            description="Nombre del servicio (``service.name``, Resource de OpenTelemetry).",
            default=configuration.service_name,
        )
        .add_configuration(
            key="sampling_ratio",
            description="Fracción de trazas raíz muestreadas (0.0 a 1.0).",
            default=configuration.sampling_ratio,
        )
        .add_configuration(
            key="console_exporter_enabled",
            description="Exporta trazas/métricas a stdout.",
            default=configuration.console_exporter_enabled,
        )
        .add_configuration(
            key="otlp_exporter_enabled",
            description="Exporta trazas/métricas vía OTLP/HTTP a un Collector.",
            default=configuration.otlp_exporter_enabled,
        )
        .add_configuration(
            key="prometheus_exporter_enabled",
            description="Expone métricas en formato Prometheus (``GET /metrics``).",
            default=configuration.prometheus_exporter_enabled,
        )
        .add_service(
            Tracer,
            lambda c: tracer,
            lifetime=Lifetime.SINGLETON,
            description="Tracer para abrir spans (tracing distribuido).",
            capabilities=("observability.tracing",),
        )
        .add_service(
            Meter,
            lambda c: meter,
            lifetime=Lifetime.SINGLETON,
            description="Meter para crear instrumentos de métricas.",
            capabilities=("observability.metrics",),
        )
        .add_healthcheck(
            name="observability.ping",
            description="Al menos un Exporter configurado (trazas y/o métricas).",
            check=health.check,
        )
        .add_event("trace.started")
        .add_event("trace.finished")
        .add_event("metric.recorded")
        .add_event("health.changed")
        .add_event("export.completed")
        .add_event("diagnostic.generated")
        .build()
    )
