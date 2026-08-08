# Plataforma de Observabilidad Empresarial — TEAF

Documentación del Sprint 2.8 (Enterprise Observability Platform, v0.8.0-alpha, [ADR-008](../architecture/adr/ADR-008-enterprise-observability-stack.md)): logging estructurado, tracing distribuido, métricas, health checks compuestos y diagnósticos, diseñados alrededor de un único motor — **OpenTelemetry** — nunca reinventado por debajo. Complementa — no reemplaza — [docs/standards/LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md), que sigue siendo la fuente normativa; este documento describe cómo TEAF la implementa.

## 1. Principio de diseño: OpenTelemetry como motor único

ADR-008 fija la decisión: TEAF nunca reimplementa lo que OpenTelemetry ya resuelve (propagación de contexto, `SpanKind`/`StatusCode`, agregación de métricas, protocolo de exportación). `teaf.observability` es una fachada delgada — sus contratos (`Tracer`, `Meter`, `Exporter`) nunca filtran tipos de `opentelemetry.*` en su firma, pero por debajo siempre hay un `TracerProvider`/`MeterProvider` real de OpenTelemetry.

```
teaf/_internal/contracts/telemetry.py   # Tracer, Span, Meter, Counter, UpDownCounter,
                                         # Histogram, Gauge, Exporter — vocabulario público

teaf/_internal/observability/
├── models.py                # SpanKind, SpanStatus, HealthCheck, HealthReport, DiagnosticReport
├── tracing/tracer.py        # OtelTracer/OtelSpan — envuelven opentelemetry.trace.Tracer/Span
├── metrics/meter.py         # OtelMeter/OtelCounter/OtelUpDownCounter/OtelHistogram/OtelGauge
├── exporters/
│   ├── console.py           # ConsoleExporter — stdout, desarrollo local
│   ├── otlp.py               # OtlpExporter — OTLP/HTTP hacia cualquier Collector
│   ├── prometheus.py           # PrometheusExporter — GET /metrics (pull)
│   └── prepared.py               # Jaeger/Zipkin/Dynatrace/Elastic/AzureMonitor/Grafana/
│                                   # Datadog/NewRelic/Splunk — contrato cumplido, ver EXPORTERS.md
├── health/checker.py        # CompositeHealthChecker — agrega ModuleHealth de cada módulo
├── diagnostics.py           # build_diagnostic_report() — RuntimeDiagnostics + HealthReport
└── middleware.py            # ObservabilityMiddleware — span raíz + duración por petición HTTP

teaf/_internal/modules/observability/   # ObservabilityModule (Module SDK) — no se expone públicamente
teaf/observability.py                    # Fachada pública — ver PUBLIC-API.md, sección 7
```

## 2. Correlación: cinco identificadores, un único ContextVar propagándolos

`teaf/_internal/core/context.py` (Core — sin dependencias hacia el resto del framework) es la única fuente real de estado de correlación:

| Identificador | ContextVar | Quién lo establece |
|---|---|---|
| `correlationId`/`requestId` | `_correlation_id_var` | `RequestIdMiddleware` (Sprint 2.1) |
| `traceId`/`spanId` | `_trace_id_var`/`_span_id_var` | `ObservabilityMiddleware`/`OtelTracer.start_span()` (Sprint 2.8) |
| `userId`/`tenant` | `_user_id_var`/`_tenant_id_var` | `SecurityMiddleware` vía `set_security_context()` (Sprint 2.8) |

`JsonFormatter` (`core/logging.py`) lee los cinco directamente de `core/context.py` — nunca importa `providers/security/` ni `observability/` (regla de capas de FRAMEWORK-BLUEPRINT.md: "Core nunca depende de ningún otro módulo del framework"). `providers/telemetry/telemetry_context.py` (Sprint 2.2) es ahora una fachada delgada sobre las mismas dos funciones de `core/context.py`, para no duplicar estado.

`OtelTracer.start_span()` sincroniza `trace_id`/`span_id` automáticamente al entrar/salir de cada span (guarda y restaura el valor anterior — soporta spans anidados sin fuga entre ellos) — ningún código de negocio llama a `set_trace_context()` a mano.

## 3. Los cinco subsistemas

| Subsistema | Documento | Resumen |
|---|---|---|
| Logging | [LOGGING.md](LOGGING.md) | JSON estructurado, `JsonFormatter`, enriquecimiento de contexto. |
| Tracing | [TRACING.md](TRACING.md) | `Tracer`/`Span`, spans padre/hijo, links, atributos, eventos. |
| Metrics | [METRICS.md](METRICS.md) | `Meter`/`Counter`/`UpDownCounter`/`Histogram`/`Gauge`. |
| Health | [HEALTH.md](HEALTH.md) | `CompositeHealthChecker`, `/health`/`/ready`/`/live`. |
| Exporters | [EXPORTERS.md](EXPORTERS.md) | Console/OTLP/Prometheus + 9 preparados. |

Runtime Diagnostics (`RuntimeDiagnostics` + `DiagnosticReport`) se documenta junto a Health, ya que `build_diagnostic_report()` envuelve ambos en un único reporte — ver [HEALTH.md](HEALTH.md), sección 4.

[OPENTELEMETRY.md](OPENTELEMETRY.md) documenta la integración con el SDK en sí (Resource, sampling, semantic conventions) — transversal a Tracing y Metrics.

## 4. `ObservabilityModule` — el Module SDK, no la API pública

Igual que `DatabaseModule`/`SecurityModule` (Sprints 2.6/2.7), `ObservabilityModule` (`teaf/_internal/modules/observability/module.py`) **no se expone** desde `teaf.observability` — construye `Resource`, `TracerProvider`, `MeterProvider` y los exportadores configurados, y expone `.tracer`/`.meter` ya listos. Una aplicación lo usa así:

```python
from teaf import Application
from teaf._internal.modules.observability.module import ObservabilityModule
from teaf._internal.modules.observability.configuration import ObservabilityConfiguration
from teaf.observability import ObservabilityMiddleware

module = ObservabilityModule(ObservabilityConfiguration(otlp_exporter_enabled=True))
app = Application(modules=[module])
app.asgi.add_middleware(ObservabilityMiddleware, tracer=module.tracer, meter=module.meter)
```

Esto es documentación interna del framework (cómo está construido `ObservabilityModule`), no una recomendación de importarlo directamente en una aplicación consumidora — el patrón público equivalente (construir `TracerProvider`/`MeterProvider` a mano y envolverlos con `OtelTracer`/`OtelMeter`) está en los 6 ejemplos de [`examples/README.md`](../../examples/README.md#plataforma-de-observabilidad-sprint-28-adr-008).

Deliberadamente **no** llama a `opentelemetry.trace.set_tracer_provider()`/`set_meter_provider()` (las funciones "globales" del SDK) — el proceso puede construir varias instancias en el mismo intérprete (cada test de la suite crea la suya) y OpenTelemetry solo permite fijar el proveedor global una vez. Cada `ObservabilityModule` queda con su propio árbol de proveedores, aislado del de cualquier otro.

## 5. Eventos publicados

`trace.started`, `trace.finished`, `metric.recorded` (publicados por `ObservabilityMiddleware` por petición HTTP), `health.changed` (publicado por `ObservabilityModule.start()` tras el primer `refresh()`), `export.completed` (publicado por `ObservabilityModule.dispose()` tras el `shutdown()` final) y `diagnostic.generated` (publicado por `build_diagnostic_report()` si se le pasa un `EventBus`) — todos vía el `EventBus` del `Runtime` (Sprint 2.3), mismo patrón que `authentication.started`/`token.created` de la plataforma de seguridad.
