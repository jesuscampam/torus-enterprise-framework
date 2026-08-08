"""Metrics — Counter, UpDownCounter, Histogram y Gauge, sobre OpenTelemetry.

Construye un ``MeterProvider`` real de OpenTelemetry conectado a un
``ConsoleExporter`` (``teaf.observability``) — cada métrica se imprime al
recolectarla (``PeriodicExportingMetricReader``, forzado aquí con
``force_flush()`` para no esperar el intervalo por defecto). ``OtelMeter``
envuelve el ``Meter`` real de OpenTelemetry sobre el contrato público
``teaf.observability.Meter``.

Ejecutar:

    python examples/metrics/main.py
"""

from __future__ import annotations

from opentelemetry.sdk.metrics import MeterProvider
from teaf.observability import ConsoleExporter, OtelMeter

metric_readers: list[object] = []
ConsoleExporter().configure_metrics(metric_readers)
provider = MeterProvider(metric_readers=metric_readers)
meter = OtelMeter(provider.get_meter("orders-service"))

# Counter — solo crece (p. ej. peticiones totales).
orders_created = meter.create_counter(
    "orders_created_total", unit="1", description="Pedidos creados."
)
orders_created.add(1, attributes={"region": "eu-west"})
orders_created.add(1, attributes={"region": "us-east"})

# UpDownCounter — sube y baja (p. ej. conexiones/trabajos activos).
active_checkouts = meter.create_up_down_counter(
    "active_checkouts", unit="1", description="Checkouts en curso."
)
active_checkouts.add(3)
active_checkouts.add(-1)

# Histogram — distribución de valores puntuales (p. ej. latencia).
order_duration = meter.create_histogram(
    "order_processing_seconds", unit="s", description="Duración de procesar un pedido."
)
for duration_seconds in (0.12, 0.45, 0.08, 1.2, 0.33):
    order_duration.record(duration_seconds, attributes={"region": "eu-west"})

# Gauge — valor puntual que sube y baja libremente (p. ej. tamaño de una cola).
queue_size = meter.create_gauge("checkout_queue_size", unit="1", description="Cola de checkout.")
queue_size.set(7)
queue_size.set(4)

provider.force_flush()
provider.shutdown()
