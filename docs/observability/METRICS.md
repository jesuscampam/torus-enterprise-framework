# Métricas — TEAF

`Meter`/`Counter`/`UpDownCounter`/`Histogram`/`Gauge` (`teaf.observability`, Sprint 2.8, ADR-008) — los cuatro instrumentos síncronos con los que se instrumenta código, tanto métricas de negocio como de framework/runtime. Ver [OBSERVABILITY.md](OBSERVABILITY.md) para cómo encaja con el resto de la plataforma.

## 1. Los cuatro instrumentos

| Instrumento | Comportamiento | Ejemplo |
|---|---|---|
| `Counter` | Solo crece | `orders_created_total`, peticiones totales, errores totales |
| `UpDownCounter` | Sube y baja | `active_connections`, trabajos en cola |
| `Histogram` | Distribución de valores puntuales | `http_request_duration_seconds`, tamaño de payload |
| `Gauge` | Último valor observado, sin acumular | `queue_size`, temperatura, memoria libre |

```python
class Meter(ABC):
    def create_counter(self, name: str, *, unit: str = "", description: str = "") -> Counter: ...
    def create_up_down_counter(self, name: str, *, unit: str = "", description: str = "") -> UpDownCounter: ...
    def create_histogram(self, name: str, *, unit: str = "", description: str = "") -> Histogram: ...
    def create_gauge(self, name: str, *, unit: str = "", description: str = "") -> Gauge: ...
```

`OtelMeter`/`OtelCounter`/`OtelUpDownCounter`/`OtelHistogram`/`OtelGauge` (`teaf/_internal/observability/metrics/meter.py`) son la única implementación (Sprint 2.8) — envuelven los instrumentos reales de `opentelemetry.metrics`.

Los instrumentos *observable* (asíncronos, con callback, p. ej. `ObservableGauge`) de OpenTelemetry no se envuelven — un consumidor que los necesite construye directamente sobre `opentelemetry.metrics` (`Meter` no lo impide, solo no lo reexpone; ver CLAUDE.md, sección 3, "no se introduce abstracción sin necesidad concreta").

## 2. Uso

```python
orders_created = meter.create_counter("orders_created_total", unit="1", description="Pedidos creados.")
orders_created.add(1, attributes={"region": "eu-west"})

order_duration = meter.create_histogram("order_processing_seconds", unit="s")
order_duration.record(0.42, attributes={"region": "eu-west"})
```

`attributes` desglosa una misma métrica por dimensión (región, status code, ...) sin crear una métrica distinta por cada valor — el backend de observabilidad agrega/filtra por atributo.

## 3. Métricas de framework/runtime

`ObservabilityMiddleware` registra `http.server.request.duration` (histograma, en segundos) por cada petición HTTP servida — con `http.request.method`/`url.path`/`http.response.status_code` como atributos. Ver [TRACING.md](TRACING.md), sección 6.

## 4. Exportación

Un instrumento no exporta nada por sí mismo — el `MeterProvider` al que pertenece (construido con los `MetricReader` de los exportadores configurados) decide cuándo y a dónde. Ver [EXPORTERS.md](EXPORTERS.md).

- **Console/OTLP** (push, periódico): `PeriodicExportingMetricReader` exporta cada `metrics_export_interval_millis` (60s por defecto) — `provider.force_flush()` fuerza una exportación inmediata (útil en scripts cortos/tests).
- **Prometheus** (pull): el valor solo se calcula cuando algo hace `GET /metrics` — no hay intervalo, no hace falta `force_flush()`.

## 5. Ejemplos ejecutables

- [`examples/metrics/`](../../examples/metrics/) — los cuatro instrumentos, con `ConsoleExporter`.
- [`examples/prometheus-metrics/`](../../examples/prometheus-metrics/) — el modelo *pull*, con `PrometheusExporter` y un endpoint `GET /metrics` real.
