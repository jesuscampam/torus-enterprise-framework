# Integración con OpenTelemetry — TEAF

Detalle de cómo TEAF usa el SDK oficial de OpenTelemetry por debajo de `teaf.observability` (Sprint 2.8, ADR-008). Ver [OBSERVABILITY.md](OBSERVABILITY.md) para la visión general y [ADR-008](../architecture/adr/ADR-008-enterprise-observability-stack.md) para la decisión completa.

## 1. SDK oficial, nunca reinventado

Dependencias (ver [STACK.md](../architecture/STACK.md)):

```
opentelemetry-api==1.44.0
opentelemetry-sdk==1.44.0
opentelemetry-exporter-otlp-proto-http==1.44.0
opentelemetry-exporter-prometheus==0.65b0
prometheus-client==0.26.0
```

TEAF nunca reimplementa lo que el SDK ya resuelve: propagación de contexto (`ContextVar`), `SpanKind`/`StatusCode`, agregación de métricas, sampling, protocolo OTLP. `teaf.observability` es una fachada delgada — `Tracer`/`Meter`/`Exporter` son contratos propios (nunca filtran tipos de `opentelemetry.*`), pero por debajo siempre hay un `TracerProvider`/`MeterProvider` real.

## 2. `Resource` — identidad del servicio

`ObservabilityModule` construye un `Resource` (semantic conventions estándar) a partir de `ObservabilityConfiguration`:

```python
Resource.create({
    ResourceAttributes.SERVICE_NAME: configuration.service_name,
    ResourceAttributes.SERVICE_VERSION: configuration.service_version,
    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: configuration.environment,
})
```

Cada span/métrica exportado incluye este `Resource` — así un backend de observabilidad puede agrupar toda la telemetría de una misma instancia/versión/entorno sin que cada span la repita individualmente.

## 3. Sampling

`ParentBased(TraceIdRatioBased(sampling_ratio))` — una traza raíz se muestrea con probabilidad `sampling_ratio` (1.0 por defecto); cualquier span hijo hereda la decisión de su padre (`ParentBased`), así una traza completa se muestrea o no como unidad, nunca a medias. Ver [TRACING.md](TRACING.md), sección 7.

## 4. `TracerProvider`/`MeterProvider` — uno por `ObservabilityModule`, nunca global

`ObservabilityModule` deliberadamente **no** llama a `opentelemetry.trace.set_tracer_provider()`/`set_meter_provider()` (las funciones "globales" del SDK) — ver [OBSERVABILITY.md](OBSERVABILITY.md), sección 4, para el razonamiento completo (varias instancias en el mismo proceso, cada test de la suite construye la suya). `OtelTracer`/`OtelMeter` llaman `.get_tracer(...)`/`.get_meter(...)` directamente sobre la instancia del provider, no sobre el registro global del SDK.

## 5. Semantic conventions

Los atributos que TEAF añade automáticamente siguen las [Semantic Conventions de OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/) — `http.request.method`, `url.path`, `http.response.status_code` (`ObservabilityMiddleware`), `service.name`/`service.version`/`deployment.environment` (`Resource`). Los atributos de negocio que añade una aplicación (`order.id`, `payment.provider`, ...) no siguen ninguna convención impuesta — son libres, como en OpenTelemetry.

## 6. Logs

OpenTelemetry también define un pilar de "Logs" (`opentelemetry-sdk-logs`) — TEAF **no** lo usa: el logging estructurado (ver [LOGGING.md](LOGGING.md)) ya resuelve correlación con trace-id/span-id vía `core/context.py`, sin necesitar el `LogRecordProcessor`/`LoggerProvider` del SDK de OpenTelemetry. Añadirlo en el futuro (para exportar logs vía OTLP junto a trazas/métricas) sería aditivo — no requeriría cambiar el esquema JSON existente.

## 7. Instrumentación automática

TEAF no incluye instrumentación automática de terceros (`opentelemetry-instrumentation-*`, p. ej. auto-instrumentar SQLAlchemy o `requests`) — el `TracerProvider`/`MeterProvider` construidos por `ObservabilityModule` son compatibles con cualquier paquete `opentelemetry-instrumentation-*` estándar que una aplicación decida añadir, sin que TEAF necesite conocerlo.

## 8. Ver también

- [TRACING.md](TRACING.md), [METRICS.md](METRICS.md), [EXPORTERS.md](EXPORTERS.md) — cada subsistema en detalle.
- [ADR-008](../architecture/adr/ADR-008-enterprise-observability-stack.md) — la decisión completa, alternativas descartadas, consecuencias.
