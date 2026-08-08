# Exportadores — TEAF

Un `Exporter` (`teaf.observability`, Sprint 2.8, ADR-008) sabe conectar trazas/métricas de OpenTelemetry hacia un backend concreto. Ver [OBSERVABILITY.md](OBSERVABILITY.md) para cómo encaja con el resto de la plataforma.

## 1. El contrato

```python
class Exporter(ABC):
    @property
    def name(self) -> str: ...
    def configure_tracing(self, tracer_provider: Any) -> None: ...
    def configure_metrics(self, metric_readers: list[Any]) -> None: ...
```

`configure_tracing` recibe un `TracerProvider` real de OpenTelemetry y le añade su `SpanProcessor`; `configure_metrics` recibe una lista mutable y le añade su `MetricReader` (no puede añadirlo directamente al `MeterProvider` — el SDK de OpenTelemetry solo acepta la lista de readers en el constructor, no después). `tracer_provider`/`metric_readers` son deliberadamente `Any` — es la única excepción documentada a la regla de no filtrar tipos de `opentelemetry.*` (ver ADR-008): el propósito exacto de `Exporter` es conectarse al SDK real, así que su firma necesita aceptarlo.

## 2. Completamente implementados

| Exportador | Backend | Notas |
|---|---|---|
| `ConsoleExporter` | stdout | `SimpleSpanProcessor` (síncrono, sin lote) — para ver el span de inmediato en desarrollo. |
| `OtlpExporter` | Cualquier OTLP Collector/HTTP | `BatchSpanProcessor`/`PeriodicExportingMetricReader` — producción. |
| `PrometheusExporter` | Prometheus (`GET /metrics`) | Solo métricas — `configure_tracing` es un no-op documentado, Prometheus no tiene noción de trazas. |

```python
from opentelemetry.sdk.trace import TracerProvider
from teaf.observability import ConsoleExporter, OtlpExporter, PrometheusExporter

provider = TracerProvider()
OtlpExporter(
    traces_endpoint="http://collector:4318/v1/traces",
    headers={"Authorization": "Bearer token"},
).configure_tracing(provider)
```

## 3. Preparados — contrato cumplido, sin conectividad nativa

`JaegerExporter`, `ZipkinExporter`, `DynatraceExporter`, `ElasticExporter`, `AzureMonitorExporter`, `GrafanaExporter`, `DatadogExporter`, `NewRelicExporter`, `SplunkExporter` — los nueve son backends con soporte OTLP nativo, así que `OtlpExporter` ya resuelve la conectividad real hacia cualquiera de ellos apuntando al Collector/endpoint correcto (ver [OPENTELEMETRY.md](OPENTELEMETRY.md)). Estas clases existen para que `name` sea un identificador estable y descubrible desde código, sin forzar a quien las instancie a saber de antemano que debe usar `OtlpExporter` en su lugar:

```python
>>> DatadogExporter().configure_tracing(provider)
NotImplementedError: El exportador 'datadog' está preparado (contrato Exporter cumplido) pero
sin conectividad nativa implementada todavía — usa OtlpExporter (teaf.observability.OtlpExporter)
apuntando al Collector/endpoint OTLP de 'datadog', o implementa este exportador de forma nativa.
```

Añadir soporte nativo real a cualquiera en el futuro es aditivo — implementar `configure_tracing`/`configure_metrics` en la subclase correspondiente no requiere tocar `Exporter` ni ningún otro exportador (ver ADR-008, sección Consecuencias).

## 4. Varios exportadores a la vez

`ObservabilityConfiguration` acepta habilitar más de uno simultáneamente (p. ej. `Console` en desarrollo + `Prometheus` para el scraping local) — cada exportador configurado añade su propio `SpanProcessor`/`MetricReader`, sin interferir entre sí:

```python
config = ObservabilityConfiguration(console_exporter_enabled=True, prometheus_exporter_enabled=True)
```

## 5. Ejemplos ejecutables

- [`examples/distributed-tracing/`](../../examples/distributed-tracing/), [`examples/metrics/`](../../examples/metrics/) — `ConsoleExporter`.
- [`examples/prometheus-metrics/`](../../examples/prometheus-metrics/) — `PrometheusExporter`.
- [`examples/opentelemetry-otlp/`](../../examples/opentelemetry-otlp/) — `OtlpExporter`, el camino hacia cualquiera de los nueve preparados.
