"""Prometheus — expone métricas OpenTelemetry en formato Prometheus vía ``GET /metrics``.

``PrometheusExporter`` (``teaf.observability``, Sprint 2.8, ADR-008) es un
``MetricReader`` de OpenTelemetry que publica en un ``CollectorRegistry`` de
``prometheus_client`` propio (``exporter.registry``) — el endpoint HTTP que
sirve el formato de texto de Prometheus lo construye la propia aplicación
(``prometheus_client.generate_latest``), TEAF no impone un framework HTTP.

Ejecutar:

    python examples/prometheus-metrics/main.py

Para servirlo de verdad y hacer ``curl http://127.0.0.1:8001/metrics``, usa
``uvicorn`` directamente sobre ``app`` (ver README.md) — este script solo
demuestra el flujo con un cliente de pruebas en memoria, igual que el resto
de ejemplos de ``examples/``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from teaf.observability import OtelMeter, PrometheusExporter

exporter = PrometheusExporter(prefix="orders_service")
metric_readers: list[object] = []
exporter.configure_metrics(metric_readers)
provider = MeterProvider(metric_readers=metric_readers)
meter = OtelMeter(provider.get_meter("orders-service"))

orders_created = meter.create_counter("orders_created_total", description="Pedidos creados.")

app = FastAPI(title="prometheus-metrics-demo")


@app.get("/orders")
def create_order() -> dict[str, bool]:
    orders_created.add(1)
    return {"ok": True}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(exporter.registry), media_type=CONTENT_TYPE_LATEST)


client = TestClient(app)

response = client.get("/orders")
print(f"GET /orders -> {response.status_code}", response.json())

response = client.get("/orders")
print(f"GET /orders -> {response.status_code}", response.json())

response = client.get("/metrics")
print(f"GET /metrics -> {response.status_code}")
for line in response.text.splitlines():
    if line.startswith("orders_service_orders_created_total"):
        print(" ", line)
