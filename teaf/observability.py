"""``teaf.observability`` — la plataforma de observabilidad empresarial de TEAF (Sprint 2.8).

Ver ADR-008 (docs/architecture/adr/ADR-008-enterprise-observability-stack.md) para el detalle
de cada decisión.

Fachada sobre ``teaf/_internal/observability/`` (adaptadores de tracing/
métricas/salud/diagnóstico/exportadores sobre OpenTelemetry) y
``teaf/_internal/contracts/telemetry.py`` (los contratos sobre los que se
diseña todo lo anterior) — un consumidor de TEAF nunca importa
``teaf._internal.observability.*`` ni ``teaf._internal.contracts.telemetry``
directamente, solo ``from teaf.observability import ...`` (o ``from teaf
import ...``, ver ``teaf/__init__.py``).

``Tracer``/``Meter``/``Exporter`` son los contratos alrededor de los que se
diseña toda la plataforma — nunca OpenTelemetry en particular (aunque hoy
sea, por decisión de ADR-008, el único motor real por debajo).
``OtelTracer``/``OtelMeter`` son las implementaciones concretas de Sprint
2.8; ``ConsoleExporter``/``OtlpExporter``/``PrometheusExporter`` están
completamente implementados, y ``JaegerExporter``/``ZipkinExporter``/
``DynatraceExporter``/``ElasticExporter``/``AzureMonitorExporter``/
``GrafanaExporter``/``DatadogExporter``/``NewRelicExporter``/
``SplunkExporter`` quedan preparados (contrato ``Exporter`` cumplido, sin
conectividad nativa propia — alcanzables hoy vía ``OtlpExporter`` + un
Collector, ver ADR-008).

Nota de nomenclatura:

- ``Logger``: no existe una clase propia — TEAF usa ``logging.Logger`` de
  la librería estándar, con logging estructurado (JSON, correlation/trace/
  span-id, user-id/tenant) aplicado por ``configure_logging()``/
  ``JsonFormatter`` (ver ``docs/observability/LOGGING.md``). El punto de
  entrada público es ``get_logger(name)``, igual que ``logging.getLogger``.
- ``HealthStatus``: ya existe como ``teaf.Health`` (alias de
  ``CapabilityHealth``, ver ``teaf/health.py``) — reexportado aquí bajo el
  mismo nombre en vez de duplicarlo con otro distinto (CLAUDE.md, DRY).
- ``TraceContext``: alias de ``TelemetryContext`` (Sprint 2.2) — el
  trace-id/span-id de la petición en curso, ver
  ``teaf/_internal/providers/telemetry/telemetry_context.py``.
- ``Metric``: OpenTelemetry no expone un tipo "métrica genérica" a nivel de
  aplicación (solo en su pipeline de exportación interno) — ``Counter``/
  ``UpDownCounter``/``Histogram``/``Gauge`` son los cuatro instrumentos
  reales con los que se instrumenta código, así que son lo que se expone
  aquí; inventar un quinto tipo genérico sin un uso concreto violaría
  CLAUDE.md, sección 3 ("no se introduce abstracción sin una necesidad
  concreta y actual").

``ObservabilityModule`` (el ``ModuleBase`` que empaqueta todo lo anterior
para ``Application(modules=[...])``) **no se expone aquí**, mismo criterio
que ``DatabaseModule``/``SecurityModule`` (ver docs/public-api/PUBLIC-API.md,
sección 6: "ningún módulo real" se expone desde ``teaf/``) — construir la
observabilidad de una aplicación con la API pública se hace componiendo
estas piezas directamente (ver ``docs/observability/OBSERVABILITY.md`` y
``examples/``), no importando el módulo del framework.
"""

from __future__ import annotations

from teaf._internal.contracts.telemetry import (
    Counter,
    Exporter,
    Gauge,
    Histogram,
    Meter,
    Span,
    TelemetryProvider,
    Tracer,
    UpDownCounter,
)
from teaf._internal.core.logging import get_logger
from teaf._internal.observability.diagnostics import build_diagnostic_report
from teaf._internal.observability.exporters.console import ConsoleExporter
from teaf._internal.observability.exporters.otlp import OtlpExporter
from teaf._internal.observability.exporters.prepared import (
    AzureMonitorExporter,
    DatadogExporter,
    DynatraceExporter,
    ElasticExporter,
    GrafanaExporter,
    JaegerExporter,
    NewRelicExporter,
    PreparedExporter,
    SplunkExporter,
    ZipkinExporter,
)
from teaf._internal.observability.exporters.prometheus import PrometheusExporter
from teaf._internal.observability.health.checker import CompositeHealthChecker
from teaf._internal.observability.metrics.meter import (
    OtelCounter,
    OtelGauge,
    OtelHistogram,
    OtelMeter,
    OtelUpDownCounter,
)
from teaf._internal.observability.middleware import ObservabilityMiddleware
from teaf._internal.observability.models import (
    DiagnosticReport,
    HealthCheck,
    HealthReport,
    SpanKind,
    SpanStatus,
)
from teaf._internal.observability.tracing.tracer import OtelSpan, OtelTracer
from teaf._internal.providers.telemetry.telemetry_context import (
    TelemetryContext,
    get_telemetry_context,
    set_telemetry_context,
)
from teaf._internal.runtime.capabilities.enums import CapabilityHealth as HealthStatus

#: Alias público de ``TelemetryContext`` — ver docstring del módulo.
TraceContext = TelemetryContext

__all__ = [
    # -- Contratos: el vocabulario alrededor del que se diseña la plataforma -----------
    "Tracer",
    "Span",
    "Meter",
    "Counter",
    "UpDownCounter",
    "Histogram",
    "Gauge",
    "Exporter",
    "TelemetryProvider",
    # -- Implementaciones concretas sobre OpenTelemetry (Sprint 2.8, ADR-008) ----------
    "OtelTracer",
    "OtelSpan",
    "OtelMeter",
    "OtelCounter",
    "OtelUpDownCounter",
    "OtelHistogram",
    "OtelGauge",
    # -- Exportadores completamente implementados --------------------------------------
    "ConsoleExporter",
    "OtlpExporter",
    "PrometheusExporter",
    # -- Exportadores preparados (contrato cumplido, sin conectividad nativa) ---------
    "PreparedExporter",
    "JaegerExporter",
    "ZipkinExporter",
    "DynatraceExporter",
    "ElasticExporter",
    "AzureMonitorExporter",
    "GrafanaExporter",
    "DatadogExporter",
    "NewRelicExporter",
    "SplunkExporter",
    # -- Vocabulario de spans -----------------------------------------------------------
    "SpanKind",
    "SpanStatus",
    # -- Salud y diagnóstico --------------------------------------------------------------
    "HealthCheck",
    "HealthReport",
    "HealthStatus",
    "CompositeHealthChecker",
    "DiagnosticReport",
    "build_diagnostic_report",
    # -- Logging estructurado -------------------------------------------------------------
    "get_logger",
    # -- Contexto de correlación/traza de la petición en curso ----------------------------
    "TraceContext",
    "TelemetryContext",
    "get_telemetry_context",
    "set_telemetry_context",
    # -- Middleware ASGI --------------------------------------------------------------------
    "ObservabilityMiddleware",
]
