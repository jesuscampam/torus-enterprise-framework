"""Structured Logging — logging JSON con correlation/trace/span-id, user-id y tenant.

``Application(settings=...)`` configura el logging del proceso (Sprint 2.1);
``get_logger()`` (``teaf.observability``, Sprint 2.8) devuelve un
``logging.Logger`` estándar cuyo formato de salida ya es JSON estructurado
(``LOGGING-STANDARD.md``). ``correlationId``/``userId``/``tenant`` solo se
propagan dentro de una petición HTTP real (``RequestIdMiddleware``/
``SecurityMiddleware`` los establecen antes de que el handler se ejecute) —
este script demuestra ``traceId``/``spanId`` (los únicos que la API pública
permite fijar fuera de una petición, vía ``TraceContext``) y deja
documentado en el README cómo se ven los demás en una petición real.

Ejecutar:

    python examples/structured-logging/main.py
"""

from __future__ import annotations

from teaf import Application, Configuration, TraceContext, get_logger, set_telemetry_context

# Construir la aplicación configura el logging del proceso (formato JSON,
# nombre de servicio) — sin esto, ``get_logger()`` seguiría funcionando,
# pero con el formato de consola legible por defecto, no JSON.
Application(settings=Configuration(log_format="json", app_name="orders-service"))

logger = get_logger("orders.checkout")

logger.info("checkout_started", extra={"context": {"cartId": "cart-42"}})

# En una petición HTTP real, ObservabilityMiddleware abre un span raíz por
# petición y sincroniza trace-id/span-id automáticamente (ver
# examples/distributed-tracing/) — aquí se fijan a mano solo para poder
# enseñar el esquema completo del log en un script standalone.
set_telemetry_context(
    TraceContext(trace_id="4bf92f3577b34da6a3ce929d0e0e4736", span_id="00f067aa0ba902b7")
)

logger.info(
    "order_created",
    extra={"context": {"orderId": "ord-1", "amount": 42.50, "currency": "EUR"}},
)

try:
    raise ZeroDivisionError("payment gateway returned a malformed amount")
except ZeroDivisionError:
    logger.error("checkout_failed", exc_info=True, extra={"context": {"cartId": "cart-42"}})

# ``module``/``capability`` no tienen ContextVar propio (una misma petición
# puede atravesar varios) — se pasan explícitamente cuando el log lo necesita.
logger.info(
    "checkout_completed",
    extra={
        "context": {"orderId": "ord-1"},
        "module_id": "orders",
        "capability": "orders.checkout",
    },
)
