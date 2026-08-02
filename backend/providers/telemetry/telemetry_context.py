"""``TelemetryContext`` — reserva el trace-id de la petición en curso.

Mismo patrón que ``backend/core/context.py`` (correlation-id) y
``providers/security/security_context.py`` (identidad). Hoy no hay ningún
backend de trazas real conectado: el valor por defecto es "sin traza
activa", tal como ya documentaba ``backend/core/logging.py`` (campo
``traceId`` reservado, ver Sprint 2.1).
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

#: Valor por defecto cuando no hay ninguna traza activa.
NO_TRACE_ID = None


@dataclass(frozen=True, slots=True)
class TelemetryContext:
    """Identificadores de traza de la petición en curso (placeholder de OpenTelemetry)."""

    trace_id: str | None = NO_TRACE_ID
    span_id: str | None = None


#: Default None (no un TelemetryContext mutable compartido) — ruff B039:
#: un objeto por defecto de ContextVar se reutiliza entre contextos que no
#: han llamado a set(), así que debe ser un primitivo inmutable.
_telemetry_context_var: ContextVar[TelemetryContext | None] = ContextVar(
    "telemetry_context", default=None
)


def set_telemetry_context(context: TelemetryContext) -> None:
    """Establece el contexto de telemetría de la petición en curso."""
    _telemetry_context_var.set(context)


def get_telemetry_context() -> TelemetryContext:
    """Devuelve el contexto de telemetría de la petición en curso (sin traza por defecto)."""
    return _telemetry_context_var.get() or TelemetryContext()
