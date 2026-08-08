# distributed-tracing/

Tracing distribuido con `Tracer`/`Span` (`teaf.observability`, Sprint 2.8, ADR-008) sobre un `TracerProvider` real de OpenTelemetry — spans padre/hijo, atributos, eventos, excepciones y estado.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- `TracerProvider`/`ConsoleExporter().configure_tracing(provider)` construyen el motor de trazas — `OtelTracer` (implementación pública de `teaf.observability.Tracer`) lo envuelve para abrir spans con la API de TEAF, nunca con la de OpenTelemetry directamente.
- `charge_payment`/`reserve_stock` son hijos de `create_order` **sin que ningún código los enlace explícitamente** — OpenTelemetry propaga el span activo por `ContextVar`, así que abrir un span dentro de otro ya activo lo convierte automáticamente en su hijo (`parent_id` en la salida).
- `reserve_stock` falla: `span.record_exception(exc)` adjunta la excepción como evento del span (no la traga), y el span de `reserve_stock` termina en `status: ERROR` — `create_order` decide, con su propio `set_status(SpanStatus.ERROR, "stock reservation failed")`, cómo se refleja el fallo en el span raíz.
- El `trace_id` es el mismo en los tres spans — es la traza completa de la operación `create_order`, reconstruible de principio a fin en cualquier backend de observabilidad (ver [`opentelemetry-otlp/`](../opentelemetry-otlp/) para exportarla a un Collector real).
