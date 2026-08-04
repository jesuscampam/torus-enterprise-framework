"""Distributed Tracing — spans padre/hijo, atributos, eventos y estado, sobre OpenTelemetry.

Construye un ``TracerProvider`` real de OpenTelemetry (una dependencia
pública ya declarada por TEAF, ver ``requirements.txt`` y ADR-008) y lo
conecta a un ``ConsoleExporter`` (``teaf.observability``) — así cada span se
imprime en cuanto se cierra. ``OtelTracer`` envuelve el ``Tracer`` real de
OpenTelemetry sobre el contrato público ``teaf.observability.Tracer``.

Ejecutar:

    python examples/distributed-tracing/main.py
"""

from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from teaf.observability import ConsoleExporter, OtelTracer, SpanKind, SpanStatus

provider = TracerProvider()
ConsoleExporter().configure_tracing(provider)
tracer = OtelTracer(provider.get_tracer("orders-service"))


def charge_payment(order_id: str) -> None:
    with tracer.start_span("charge_payment", kind=SpanKind.CLIENT) as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("payment.provider", "stripe")
        span.add_event("payment.authorized")
        span.set_status(SpanStatus.OK)


def reserve_stock(order_id: str) -> None:
    with tracer.start_span("reserve_stock") as span:
        span.set_attribute("order.id", order_id)
        try:
            raise RuntimeError("out of stock")
        except RuntimeError as exc:
            span.record_exception(exc)
            raise


def create_order(order_id: str) -> None:
    # Span raíz — "create_order" es el padre de "charge_payment" y
    # "reserve_stock" porque OpenTelemetry propaga el span activo por
    # ContextVar (sin pasarlo explícitamente por parámetro).
    with tracer.start_span("create_order", kind=SpanKind.SERVER) as span:
        span.set_attribute("order.id", order_id)
        charge_payment(order_id)
        try:
            reserve_stock(order_id)
        except RuntimeError:
            span.set_status(SpanStatus.ERROR, "stock reservation failed")
            return
        span.set_status(SpanStatus.OK)


create_order("ord-1")
provider.shutdown()
