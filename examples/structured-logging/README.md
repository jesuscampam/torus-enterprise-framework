# structured-logging/

Logging JSON estructurado con `get_logger()` (`teaf.observability`, Sprint 2.8, ADR-008) — correlation-id, trace-id/span-id, user-id/tenant, nivel, mensaje y contexto libre, sin ninguna línea de negocio formateando texto a mano.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- `Application(settings=Configuration(log_format="json", ...))` configura el logging del proceso — `get_logger(name)` es solo `logging.getLogger(name)`, el formato JSON lo aplica `configure_logging()` por debajo.
- Cada línea de log es un objeto JSON con el esquema fijo de [`LOGGING-STANDARD.md`](../../docs/standards/LOGGING-STANDARD.md): `timestamp`, `level`, `service`, `environment`, `correlationId`, `requestId`, `traceId`, `spanId`, `userId`, `tenant`, `message`, `context`.
- `traceId`/`spanId` se fijan aquí a mano con `set_telemetry_context(TraceContext(...))` solo para poder verlos en un script standalone — en una aplicación real, `ObservabilityMiddleware` (ver [`distributed-tracing/`](../distributed-tracing/)) los sincroniza automáticamente durante cada petición HTTP.
- `correlationId`/`userId`/`tenant` quedan en `"-"`/`null` aquí (no hay petición HTTP en curso) — en una aplicación real, `RequestIdMiddleware` y `SecurityMiddleware` los establecen antes de que el handler se ejecute, sin que el código de negocio los pase a mano.
- `module`/`capability` no tienen contexto global propio (una misma petición puede atravesar varios) — se añaden explícitamente vía `extra={"module_id": ..., "capability": ...}` cuando un log concreto lo necesita.
- Una excepción capturada con `exc_info=True` añade el campo `exception` (traceback completo) al JSON, sin que el logger normal la trague en silencio.
