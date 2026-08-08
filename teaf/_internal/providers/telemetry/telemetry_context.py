"""``TelemetryContext`` — el trace-id/span-id de la petición en curso.

Mismo patrón que ``core/context.py`` (correlation-id) y
``providers/security/security_context.py`` (identidad). Desde Sprint 2.8
(ADR-007 → ADR-008) ``core/context.py`` es la única fuente real de este
estado (``set_trace_context``/``get_trace_id``/``get_span_id``) — este
módulo queda como una fachada de conveniencia con forma de dataclass sobre
esas mismas funciones, poblada de verdad por
``teaf._internal.observability.middleware.ObservabilityMiddleware`` (antes,
Sprint 2.1-2.7, quedaba siempre en blanco: ningún middleware la establecía).
"""

from __future__ import annotations

from dataclasses import dataclass

from teaf._internal.core.context import get_span_id, get_trace_id, set_trace_context

#: Valor por defecto cuando no hay ninguna traza activa.
NO_TRACE_ID = None


@dataclass(frozen=True, slots=True)
class TelemetryContext:
    """Identificadores de traza de la petición en curso."""

    trace_id: str | None = NO_TRACE_ID
    span_id: str | None = None


def set_telemetry_context(context: TelemetryContext) -> None:
    """Establece el contexto de telemetría de la petición en curso."""
    set_trace_context(trace_id=context.trace_id, span_id=context.span_id)


def get_telemetry_context() -> TelemetryContext:
    """Devuelve el contexto de telemetría de la petición en curso (sin traza por defecto)."""
    return TelemetryContext(trace_id=get_trace_id(), span_id=get_span_id())
