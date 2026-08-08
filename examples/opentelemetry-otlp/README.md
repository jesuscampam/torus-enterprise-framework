# opentelemetry-otlp/

Trazas y métricas exportadas vía OTLP/HTTP con `OtlpExporter` (`teaf.observability`, Sprint 2.8, ADR-008) — el "camino universal" hacia cualquier backend con soporte OTLP.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

Sin un Collector escuchando en `localhost:4318`, verás varios avisos de reintento en la salida — es el comportamiento normal de `BatchSpanProcessor`/`PeriodicExportingMetricReader` (exportan en un hilo de fondo, sin tumbar el proceso si el backend no responde). Para verlo llegar de verdad a un backend:

```bash
docker run -p 4318:4318 otel/opentelemetry-collector:latest
python main.py
```

## Qué observar

- `OtlpExporter(traces_endpoint=..., metrics_endpoint=..., headers=...)` es el único exportador que necesitas conocer para llegar a Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog, New Relic o Splunk — todos alcanzables vía su propio OpenTelemetry Collector/endpoint OTLP, sin escribir un exportador nuevo por backend (ver [ADR-008](../../docs/architecture/adr/ADR-008-enterprise-observability-stack.md)).
- `teaf.observability` también expone una clase preparada por cada uno de esos nueve backends (`JaegerExporter`, `DatadogExporter`, ...) — con el contrato `Exporter` cumplido (`.name` estable) pero sin conectividad nativa propia todavía; usarlas hoy lanza `NotImplementedError` con un mensaje que señala directamente a `OtlpExporter` como alternativa ya funcional.
- `tracer_provider.shutdown()`/`meter_provider.shutdown()` fuerzan el flush final antes de salir — sin esto, el último lote en el buffer podría perderse si el proceso termina antes de que el hilo de fondo lo envíe.
- `headers={"Authorization": "Bearer ..."}` es como se autentica contra un Collector/backend que lo exija (Datadog, New Relic, Grafana Cloud, ...) — el mismo parámetro sirve para cualquiera de ellos.
