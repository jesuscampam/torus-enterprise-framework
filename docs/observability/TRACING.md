# Tracing Distribuido — TEAF

`Tracer`/`Span` (`teaf.observability`, Sprint 2.8, ADR-008) — el contrato central de tracing distribuido. Ver [OBSERVABILITY.md](OBSERVABILITY.md) para cómo encaja con el resto de la plataforma.

## 1. Los contratos

```python
class Span(ABC):
    trace_id: str          # propiedad, hexadecimal (32 caracteres)
    span_id: str            # propiedad, hexadecimal (16 caracteres)
    def set_attribute(self, key: str, value: str | bool | int | float) -> None: ...
    def add_event(self, name: str, *, attributes: Mapping[str, object] | None = None) -> None: ...
    def record_exception(self, exception: BaseException) -> None: ...
    def set_status(self, status: SpanStatus, description: str | None = None) -> None: ...

class Tracer(ABC):
    def start_span(
        self, name: str, *, kind: SpanKind = SpanKind.INTERNAL,
        attributes: Mapping[str, object] | None = None, links: Sequence[Span] = (),
    ) -> AbstractContextManager[Span]: ...
```

`OtelTracer`/`OtelSpan` (`teaf/_internal/observability/tracing/tracer.py`) son la única implementación (Sprint 2.8) — envuelven `opentelemetry.trace.Tracer`/`Span` reales, sin filtrar sus tipos en la firma pública.

## 2. Spans padre/hijo — automático, sin pasar contexto a mano

```python
with tracer.start_span("create_order", kind=SpanKind.SERVER) as span:
    span.set_attribute("order.id", order_id)
    with tracer.start_span("charge_payment") as child:   # hijo automático de "create_order"
        child.add_event("payment.authorized")
```

OpenTelemetry propaga el span activo por `ContextVar` — abrir un span dentro de otro ya activo lo convierte en su hijo sin que ningún código lo enlace explícitamente. Dos spans abiertos como parte de la misma cadena de llamadas comparten `trace_id` pero tienen `span_id` distintos.

## 3. `links` — relacionar sin ser padre

```python
with tracer.start_span("background_job", links=(triggering_request_span,)):
    ...
```

Un `Link` referencia un span de **otra** traza causalmente relacionado (p. ej. un job en background disparado por una petición HTTP) sin convertirlo en su padre directo — la petición original y el job quedan enlazados, pero cada uno conserva su propio `trace_id`.

## 4. Excepciones y estado

```python
try:
    reserve_stock(order_id)
except OutOfStockError as exc:
    span.record_exception(exc)          # adjunta la excepción como evento
    span.set_status(SpanStatus.ERROR, "stock reservation failed")
```

`record_exception()` no suprime la excepción — el `raise`/propagación sigue el flujo normal de Python. `OpenTelemetry` también registra automáticamente cualquier excepción no capturada que escape del bloque `with tracer.start_span(...)`, marcando el span como `ERROR` — `record_exception()` es para excepciones que sí capturas y manejas, pero cuyo fallo quieres que quede visible en la traza.

## 5. Sincronización con `core/context.py`

`OtelTracer.start_span()` sincroniza `trace_id`/`span_id` en `core/context.py` mientras el span está activo (guarda y restaura el valor anterior al salir — soporta anidamiento sin fuga) — así `JsonFormatter` incluye el `traceId`/`spanId` correctos en cada log emitido dentro del span, sin que `core/logging.py` conozca OpenTelemetry. Ver [LOGGING.md](LOGGING.md), sección 3.

## 6. `ObservabilityMiddleware` — el span raíz por petición HTTP

```python
app.asgi.add_middleware(ObservabilityMiddleware, tracer=tracer, meter=meter)
```

Abre un span `SERVER` por petición (`{method} {path}`), registra `http.request.method`/`url.path`/`http.response.status_code`, marca `ERROR` si el status es `>= 500` o la petición lanza una excepción, y registra la duración como histograma (`http.server.request.duration`, ver [METRICS.md](METRICS.md)). Publica `trace.started`/`trace.finished`/`metric.recorded` en el `EventBus`.

## 7. Sampling

`ObservabilityConfiguration.sampling_ratio` (0.0 a 1.0, por defecto 1.0) controla qué fracción de trazas **raíz** se muestrean, vía `ParentBased(TraceIdRatioBased(ratio))` de OpenTelemetry — un span hijo hereda la decisión de muestreo de su padre (no se decide de forma independiente por span), así una traza completa se muestrea o no como unidad. Ver [OPENTELEMETRY.md](OPENTELEMETRY.md), sección 3.

## 8. Ejemplo ejecutable

[`examples/distributed-tracing/`](../../examples/distributed-tracing/) — spans padre/hijo, atributos, eventos, excepciones y estado, de principio a fin.
