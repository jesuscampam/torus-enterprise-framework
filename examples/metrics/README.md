# metrics/

Los cuatro instrumentos de métricas de `Meter` (`teaf.observability`, Sprint 2.8, ADR-008) — `Counter`, `UpDownCounter`, `Histogram`, `Gauge` — sobre un `MeterProvider` real de OpenTelemetry.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- `MeterProvider`/`ConsoleExporter().configure_metrics(readers)` construyen el motor de métricas — `OtelMeter` (implementación pública de `teaf.observability.Meter`) lo envuelve para crear instrumentos con la API de TEAF.
- `Counter` (`orders_created_total`) solo crece — sirve para totales acumulados (peticiones, pedidos, errores).
- `UpDownCounter` (`active_checkouts`) sube y baja — sirve para valores que se incrementan y decrementan (conexiones activas, trabajos en cola).
- `Histogram` (`order_processing_seconds`) agrega una distribución de valores puntuales — percentiles de latencia, tamaños de payload.
- `Gauge` (`checkout_queue_size`) es un valor puntual que se sobrescribe — el último valor observado, sin acumular histórico.
- `attributes={"region": "eu-west"}` en cada llamada demuestra cómo una misma métrica se desglosa por dimensión (región, status code, ...) sin crear una métrica distinta por cada valor.
- `provider.force_flush()` fuerza la exportación inmediata — en producción, `PeriodicExportingMetricReader` exporta cada `metrics_export_interval_millis` sin que el código de negocio tenga que forzarlo.
