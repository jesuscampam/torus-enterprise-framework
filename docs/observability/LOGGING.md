# Logging Estructurado — TEAF

Implementación de [docs/standards/LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md), sección 1. Ver [OBSERVABILITY.md](OBSERVABILITY.md) para cómo encaja con el resto de la plataforma.

## 1. `get_logger()` — el único punto de entrada

```python
from teaf.observability import get_logger

logger = get_logger("orders.checkout")
logger.info("order_created", extra={"context": {"orderId": "ord-1", "amount": 42.5}})
```

`get_logger(name)` es literalmente `logging.getLogger(name)` — un `logging.Logger` estándar de la librería estándar de Python, sin ninguna subclase propia. El formato JSON lo aplica el handler configurado por `configure_logging()` (composition root, `teaf/_internal/core/application.py`), no el logger en sí — por eso el mismo código funciona igual en consola (desarrollo) que en JSON (producción), sin cambiar una línea.

## 2. El esquema JSON

```json
{
  "timestamp": "2026-08-04T20:52:34.350Z",
  "level": "INFO",
  "service": "teaf-backend",
  "environment": "production",
  "correlationId": "b3f1c2e4-9a11-4d2f-8b3a-6f2e1d4c9a01",
  "requestId": "b3f1c2e4-9a11-4d2f-8b3a-6f2e1d4c9a01",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "spanId": "00f067aa0ba902b7",
  "userId": "user-789",
  "tenant": "tenant-acme",
  "message": "order_created",
  "context": { "orderId": "ord-1", "amount": 42.5 }
}
```

`requestId` es siempre igual a `correlationId` (mismo valor, dos claves — el nombre "Request Id" viene del bootstrap del framework, ver `docs/core/CORE.md`; "Correlation Id" es el término usado en `LOGGING-STANDARD.md`). Ningún campo se omite del JSON — los que no aplican (sin traza activa, sin identidad resuelta) van como `null`, nunca se eliden, para que el esquema sea siempre el mismo.

`module`/`capability` **sí** se omiten cuando no se pasan — a diferencia de los cinco anteriores, no tienen `ContextVar` propio (una misma petición HTTP puede atravesar varios módulos/capacidades), así que se añaden explícitamente por log:

```python
logger.info(
    "checkout_completed",
    extra={"context": {"orderId": "ord-1"}, "module_id": "orders", "capability": "orders.checkout"},
)
```

## 3. De dónde sale cada campo

| Campo | Origen | Ver |
|---|---|---|
| `correlationId`/`requestId` | `RequestIdMiddleware` (Sprint 2.1) | `core/context.py::get_correlation_id()` |
| `traceId`/`spanId` | `ObservabilityMiddleware`/`OtelTracer.start_span()` (Sprint 2.8) | [TRACING.md](TRACING.md), sección 3 |
| `userId`/`tenant` | `SecurityMiddleware` vía `set_security_context()` (Sprint 2.8) | `providers/security/security_context.py` |
| `environment` | Parámetro de `configure_logging()`, resuelto de `Settings.environment` | `core/application.py` |
| `service` | Parámetro `service_name` de `configure_logging()` | `DEFAULT_SERVICE_NAME` |

Los tres primeros son `ContextVar` (seguros en código asíncrono concurrente — cada petición ASGI corre en su propio `asyncio.Task`, sin fuga entre peticiones concurrentes); `environment`/`service` son estáticos por proceso.

## 4. Excepciones

```python
try:
    ...
except ValueError:
    logger.error("checkout_failed", exc_info=True, extra={"context": {"cartId": cart_id}})
```

`exc_info=True` añade el campo `"exception"` con el traceback completo — nunca se traga en silencio, nunca se trunca.

## 5. Qué NO loguear

Ver [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md) y [LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md), sección 4 — contraseñas, tokens JWT completos, claves API, PII más allá de identificadores técnicos.

## 6. Ejemplo ejecutable

[`examples/structured-logging/`](../../examples/structured-logging/) — el esquema completo, incluyendo trace-id/span-id y `module`/`capability`.
