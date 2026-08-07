"""``ObservabilityModule`` — el módulo oficial de observabilidad de TEAF, sobre el Module SDK.

Mismo patrón que ``DatabaseModule``/``SecurityModule``: todo lo concreto
(``Resource``, ``TracerProvider``, ``MeterProvider``, exportadores,
``Tracer``, ``Meter``) se construye en ``__init__`` — no en
``initialize()`` — porque ``ModuleBase.bootstrap()`` llama a
``get_manifest()`` **antes** de ejecutar cualquier hook del ciclo de vida.

Deliberadamente **no** llama a ``opentelemetry.trace.set_tracer_provider``/
``set_meter_provider`` (las funciones "globales" del SDK): el proceso
puede construir varias ``Application``/``ObservabilityModule`` en el mismo
intérprete (cada test de la suite crea la suya) y el SDK de OpenTelemetry
solo permite fijar el proveedor global una vez — un segundo intento emite
un warning y se ignora. En su lugar, ``self.tracer_provider``/
``self.meter_provider`` se guardan como atributos de instancia y
``OtelTracer``/``OtelMeter`` envuelven ``.get_tracer(...)``/
``.get_meter(...)`` llamados directamente sobre esa instancia — cada
``ObservabilityModule`` queda con su propio árbol de proveedores,
aislado del de cualquier otro.

``tracer``/``meter`` quedan disponibles como atributos públicos
inmediatamente después de construir el módulo — **antes** de pasarlo a
``Application(modules=[...])`` — porque ``ObservabilityMiddleware`` los
necesita para configurarse, igual que ``SecurityMiddleware`` con
``provider_registry``/``principal_resolver`` (ver
``security/module.py``).
"""

from __future__ import annotations

from typing import Any

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes
from teaf._internal.contracts.telemetry import Exporter
from teaf._internal.modules.observability.configuration import ObservabilityConfiguration
from teaf._internal.modules.observability.health import ObservabilityHealth
from teaf._internal.modules.observability.manifest import build_observability_manifest
from teaf._internal.observability.exporters.console import ConsoleExporter
from teaf._internal.observability.exporters.otlp import OtlpExporter
from teaf._internal.observability.exporters.prometheus import PrometheusExporter
from teaf._internal.observability.metrics.meter import OtelMeter
from teaf._internal.observability.tracing.tracer import OtelTracer
from teaf._internal.runtime.event_bus import Event
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase

_INSTRUMENTATION_NAME = "teaf"


class ObservabilityModule(ModuleBase):
    """Plataforma de observabilidad: tracing, métricas, health y exportadores."""

    def __init__(
        self,
        configuration: ObservabilityConfiguration | None = None,
        *,
        extra_exporters: tuple[Exporter, ...] = (),
    ) -> None:
        """``extra_exporters`` es donde se pasan exportadores preparados
        (``JaegerExporter``, ``DatadogExporter``, uno propio, ...) que este
        módulo no construye automáticamente — Console/OTLP/Prometheus sí,
        cuando su flag de configuración correspondiente está activo."""
        super().__init__()
        self.configuration = configuration or ObservabilityConfiguration()

        self.resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: self.configuration.service_name,
                ResourceAttributes.SERVICE_VERSION: self.configuration.service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.configuration.environment,
            }
        )

        exporters: list[Exporter] = []
        if self.configuration.console_exporter_enabled:
            exporters.append(
                ConsoleExporter(
                    export_interval_millis=self.configuration.metrics_export_interval_millis
                )
            )
        if self.configuration.otlp_exporter_enabled:
            exporters.append(
                OtlpExporter(
                    traces_endpoint=self.configuration.otlp_traces_endpoint,
                    metrics_endpoint=self.configuration.otlp_metrics_endpoint,
                    headers=dict(self.configuration.otlp_headers) or None,
                    timeout_seconds=self.configuration.otlp_timeout_seconds,
                    export_interval_millis=self.configuration.metrics_export_interval_millis,
                )
            )
        self.prometheus_exporter: PrometheusExporter | None = None
        if self.configuration.prometheus_exporter_enabled:
            self.prometheus_exporter = PrometheusExporter(
                prefix=self.configuration.prometheus_prefix
            )
            exporters.append(self.prometheus_exporter)
        exporters.extend(extra_exporters)
        self.exporters: tuple[Exporter, ...] = tuple(exporters)

        self.tracer_provider = TracerProvider(
            resource=self.resource,
            sampler=ParentBased(TraceIdRatioBased(self.configuration.sampling_ratio)),
        )
        if self.configuration.tracing_enabled:
            for exporter in self.exporters:
                exporter.configure_tracing(self.tracer_provider)

        # ``list[Any]`` y no ``list[MetricReader]``: el contrato
        # ``Exporter.configure_metrics`` (contracts/telemetry.py) recibe
        # ``list[Any]`` precisamente para no filtrar tipos de OpenTelemetry,
        # así que esta lista es el otro extremo de esa misma frontera.
        metric_readers: list[Any] = []
        if self.configuration.metrics_enabled:
            for exporter in self.exporters:
                exporter.configure_metrics(metric_readers)
        self.meter_provider = MeterProvider(resource=self.resource, metric_readers=metric_readers)

        self.tracer = OtelTracer(self.tracer_provider.get_tracer(_INSTRUMENTATION_NAME))
        self.meter = OtelMeter(self.meter_provider.get_meter(_INSTRUMENTATION_NAME))

        self.health = ObservabilityHealth(self.exporters)

    def get_manifest(self) -> ModuleManifest:
        return build_observability_manifest(
            self.configuration, tracer=self.tracer, meter=self.meter, health=self.health
        )

    async def start(self, context: ModuleContext) -> None:
        """Refresca la caché de salud — sin I/O de red que abrir (el SDK ya está listo)."""
        status = await self.health.refresh()
        context.runtime.event_bus.publish(
            Event(
                name="health.changed", payload={"module": "observability", "status": status.value}
            )
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info(
            "observability_module_ready",
            extra={"context": {"exporters": [exporter.name for exporter in self.exporters]}},
        )

    async def dispose(self, context: ModuleContext) -> None:
        """Vacía y cierra los proveedores — fuerza el flush final de cualquier exportador
        con buffer (``BatchSpanProcessor``/``PeriodicExportingMetricReader``)."""
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()
        context.runtime.event_bus.publish(
            Event(
                name="export.completed",
                payload={"exporters": [exporter.name for exporter in self.exporters]},
            )
        )
