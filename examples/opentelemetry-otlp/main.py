"""OpenTelemetry — exportar trazas y métricas vía OTLP/HTTP a un Collector real.

``OtlpExporter`` (``teaf.observability``, Sprint 2.8, ADR-008) es el
"camino universal" documentado en ADR-008: cualquier backend con soporte
OTLP (Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog,
New Relic, Splunk — todos con una clase preparada en ``teaf.observability``,
ver ``docs/observability/EXPORTERS.md``) es alcanzable apuntando este mismo
exportador a su Collector, sin escribir un exportador nuevo.

No requiere que haya un Collector escuchando para poder ejecutarse:
``BatchSpanProcessor``/``PeriodicExportingMetricReader`` exportan en un
hilo de fondo y registran un aviso (no una excepción) si el envío falla —
en ese caso el script termina igual, solo sin datos realmente entregados.
Para verlo funcionar de verdad, arranca un OpenTelemetry Collector local:

    docker run -p 4318:4318 otel/opentelemetry-collector:latest

Ejecutar:

    python examples/opentelemetry-otlp/main.py
"""

from __future__ import annotations

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from teaf.observability import OtelMeter, OtelTracer, OtlpExporter, SpanKind, SpanStatus

exporter = OtlpExporter(
    traces_endpoint="http://localhost:4318/v1/traces",
    metrics_endpoint="http://localhost:4318/v1/metrics",
    headers={"Authorization": "Bearer demo-token"},
    export_interval_millis=1_000,
)

tracer_provider = TracerProvider()
exporter.configure_tracing(tracer_provider)
tracer = OtelTracer(tracer_provider.get_tracer("orders-service"))

metric_readers: list[object] = []
exporter.configure_metrics(metric_readers)
meter_provider = MeterProvider(metric_readers=metric_readers)
meter = OtelMeter(meter_provider.get_meter("orders-service"))

requests_total = meter.create_counter("orders_created_total")

with tracer.start_span("create_order", kind=SpanKind.SERVER) as span:
    span.set_attribute("order.id", "ord-1")
    requests_total.add(1, attributes={"order.id": "ord-1"})
    span.set_status(SpanStatus.OK)

# ``shutdown()`` fuerza el flush final antes de que el proceso termine — sin
# esto, el batch en curso podría perderse si el proceso sale antes de que el
# hilo de fondo lo envíe.
tracer_provider.shutdown()
meter_provider.shutdown()

print(
    "Traza y métrica enviadas vía OTLP a http://localhost:4318 "
    "(si había un Collector escuchando)."
)
