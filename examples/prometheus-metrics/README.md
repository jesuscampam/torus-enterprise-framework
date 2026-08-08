# prometheus-metrics/

Métricas OpenTelemetry expuestas en formato Prometheus (`GET /metrics`) con `PrometheusExporter` (`teaf.observability`, Sprint 2.8, ADR-008) — modelo *pull*, no *push*.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

`main.py` demuestra el flujo con un `TestClient` en memoria (igual que el resto de `examples/`, para poder ejecutarse de principio a fin sin dejar un servidor colgado). Para servirlo de verdad:

```bash
uvicorn main:app --app-dir examples/prometheus-metrics --port 8001
curl http://127.0.0.1:8001/orders    # incrementa el contador
curl http://127.0.0.1:8001/metrics   # formato de texto de Prometheus
```

## Qué observar

- `PrometheusExporter` es un `MetricReader` de OpenTelemetry (igual que `ConsoleExporter`/`OtlpExporter`) que publica en su propio `CollectorRegistry` de `prometheus_client` (`exporter.registry`) — no expone un servidor HTTP por sí mismo, a propósito: TEAF no impone qué framework HTTP sirve `/metrics`.
- El endpoint `GET /metrics` lo construye la propia aplicación con `prometheus_client.generate_latest(exporter.registry)` — tres líneas de FastAPI, sin ninguna dependencia nueva de TEAF.
- `prefix="orders_service"` antepone ese prefijo a cada métrica exportada (`orders_service_orders_created_total`) — útil para namespacing cuando varios servicios comparten un mismo Prometheus.
- A diferencia de Console/OTLP (que exportan en un intervalo periódico), Prometheus es *pull*: el valor solo se calcula cuando algo hace `GET /metrics` — por eso `PrometheusExporter` no necesita un `force_flush()` como en [`metrics/`](../metrics/).
