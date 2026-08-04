# ADR-008: Enterprise Observability Stack — OpenTelemetry, Prometheus, Diagnostics

## Estado

Aceptado

## Contexto

TEAF llega al Sprint 2.8 con observabilidad únicamente como contratos abstractos y andamiaje sin cablear: `TelemetryProvider` (`teaf/_internal/contracts/telemetry.py`, Sprint 2.2) sin implementación; `TracerProvider`/`MetricsProvider`/`LoggerProvider` (`teaf/_internal/providers/telemetry/`) todos abstractos, ninguno instanciado en ningún sitio; `TelemetryContext` (`telemetry_context.py`) ya con la forma de un `ContextVar` de trace/span, pero que ningún middleware llega a poblar nunca; `JsonFormatter` (`teaf/_internal/core/logging.py`) que ya emite el esquema JSON completo de [LOGGING-STANDARD.md](../../standards/LOGGING-STANDARD.md) salvo por un `traceId` fijado explícitamente a `null` ("Reservado para OpenTelemetry — no implementado en Sprint 2.1"); y `RuntimeDiagnostics` (`teaf/_internal/runtime/diagnostics.py`) con `memory_placeholder`/`cpu_placeholder` literales, documentados como huecos deliberados a rellenar en un Sprint futuro. `docs/architecture/STACK.md` ya había decidido, desde Sprint 1, que la plataforma se construiría sobre OpenTelemetry ("estándar abierto y neutral de proveedor... compatible tanto con Azure Monitor como con Grafana/Jaeger") — pero sin fijar todavía ninguna versión de paquete concreta, porque ninguna implementación real existía aún.

## Problema

¿Cómo construye TEAF una plataforma de observabilidad empresarial completa (logging estructurado con trace-id real, tracing distribuido, métricas, health checks agregados, diagnósticos de runtime, y exportación hacia múltiples backends) sin romper ni duplicar lo que Sprint 2.1-2.4 ya construyó (correlation-id, `JsonFormatter`, `RuntimeDiagnostics`, `EventBus`, `CapabilityHealth`), y qué librerías de terceros necesita, dado que STACK.md ya comprometió la dirección (OpenTelemetry) pero ningún paquete está instalado todavía?

## Decisión

Se completa — nunca se reemplaza — el andamiaje de Sprint 2.1-2.4: `TelemetryContext` pasa a poblarse realmente (vía una nueva `ObservabilityMiddleware`, mismo patrón que `RequestIdMiddleware`), `JsonFormatter.traceId` deja de ser `null` fijo y lee el trace-id activo, `RuntimeDiagnostics` reemplaza sus dos placeholders por memoria/CPU reales (vía el módulo estándar `resource`, sin dependencia nueva), y `CapabilityHealth`/`CapabilityCategory.OBSERVABILITY` (ya existentes desde Sprint 2.4) se reutilizan sin duplicar vocabulario.

Se adopta el **SDK oficial de OpenTelemetry para Python** (`opentelemetry-api`/`opentelemetry-sdk`) como motor único de trazas y métricas — nunca una abstracción propia por debajo, para no reinventar semantic conventions, sampling ni context propagation ya resueltos por el estándar. Sobre ese SDK se implementan completamente tres exportadores: **Console** (desarrollo/debug, sin infraestructura externa), **OTLP** (`opentelemetry-exporter-otlp-proto-http` — el protocolo nativo de OpenTelemetry, compatible con Azure Monitor, Grafana Tempo/Mimir, Jaeger, y cualquier Collector), y **Prometheus** (`opentelemetry-exporter-prometheus` + `prometheus-client` — expone `/metrics` en formato Prometheus a partir de las mismas métricas OTel, sin un pipeline de instrumentación paralelo). El resto de backends nombrados en el Sprint (Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog, New Relic, Splunk) quedan como **contrato preparado** (`Exporter` ABC, una subclase por backend sin cuerpo) — todos son, en la práctica, consumidores de OTLP o de Prometheus, así que ya son alcanzables hoy sin código adicional vía un OpenTelemetry Collector intermedio; el contrato solo formaliza la extensión directa si una aplicación necesita un exportador nativo propio.

Ver justificación completa por librería en [STACK.md](../STACK.md).

## Consecuencias

### Positivas

- Ningún backend de observabilidad futuro exige cambios en el Runtime, el `ServiceContainer`, el `EventBus` ni la superficie pública `teaf.*` — Console/OTLP/Prometheus cubren, en la práctica, cualquier backend real vía un Collector; un `Exporter` nativo nuevo es una clase más, nunca un rediseño.
- El trabajo de Sprint 2.1-2.4 (correlation-id, `JsonFormatter`, `RuntimeDiagnostics`, `CapabilityHealth`) se completa en vez de descartarse — cero reescritura de lo ya aceptado, solo relleno de los huecos que esos Sprints dejaron documentados a propósito.
- Adoptar el SDK oficial de OpenTelemetry (en vez de una abstracción propia) da acceso inmediato a semantic conventions, sampling y context propagation ya estandarizados, sin mantenerlos internamente.
- `RuntimeDiagnostics` gana memoria/CPU reales sin ninguna dependencia nueva (`resource`, estándar de Python) — el diagnóstico más barato es el que no añade superficie de dependencias.

### Negativas / Trade-offs

- Cinco paquetes nuevos de terceros (`opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-exporter-prometheus`, `prometheus-client`) amplían la superficie de dependencias del framework — cada uno fijado a versión exacta, mismo proceso de actualización que el resto del stack (Dependabot).
- `opentelemetry-exporter-prometheus` es un paquete `0.x` (pre-1.0, "beta" en el versionado propio de OpenTelemetry para exportadores no-core) — su API es menos estable que `opentelemetry-api`/`-sdk` (ya en `1.x`); un futuro upgrade puede requerir ajustes que las librerías `1.x` no exigirían.
- Jaeger/Zipkin/Dynatrace/Elastic/Azure Monitor/Grafana/Datadog/New Relic/Splunk no tienen implementación concreta en este Sprint — quedan como superficie preparada (`Exporter` ABC), alcanzables hoy solo indirectamente vía OTLP + Collector, no como integración nativa entregada.
- `resource` (usado para memoria/CPU en `RuntimeDiagnostics`) es una API POSIX — no funciona en Windows; ya documentado como limitación conocida, consistente con el resto del stack (Docker/Linux first, ver ADR-005).
