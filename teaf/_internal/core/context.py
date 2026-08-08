"""Contexto de petición propagado entre middleware/, core/ y logging.

Expone el correlation-id (también llamado "Request ID" en el bootstrap,
ver docs/core/CORE.md) de la petición HTTP en curso a través de un
``ContextVar``, para que cualquier capa —sin recibirlo explícitamente por
parámetro— pueda incluirlo en sus logs (ver docs/standards/LOGGING-STANDARD.md,
sección 2). Es la única pieza de estado "global" permitida por el framework,
precisamente porque ``ContextVar`` es seguro en código asíncrono concurrente
(cada request tiene su propio valor aislado).
"""

from __future__ import annotations

from contextvars import ContextVar

#: Valor por defecto cuando no hay una petición HTTP en curso (por ejemplo,
#: en tareas de arranque o en pruebas unitarias que no pasan por el middleware).
NO_CORRELATION_ID = "-"

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default=NO_CORRELATION_ID)


def set_correlation_id(correlation_id: str) -> None:
    """Establece el correlation-id de la petición en curso."""
    _correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """Devuelve el correlation-id de la petición en curso, o ``NO_CORRELATION_ID``."""
    return _correlation_id_var.get()


#: Trace-id/span-id de la petición en curso (Sprint 2.8, ver ADR-008) — mismo
#: patrón que el correlation-id de arriba. ``None`` por defecto (sin traza
#: activa), a diferencia de ``NO_CORRELATION_ID`` (un centinela ``str``)
#: porque ``teaf._internal.providers.telemetry.telemetry_context.TelemetryContext``
#: ya estableció esa convención en Sprint 2.2 y este módulo es ahora su única
#: fuente real de estado — ``providers/telemetry/`` delega aquí en vez de
#: mantener su propio ``ContextVar`` (providers/ puede depender de core/, la
#: dirección inversa rompería "Core nunca depende de ningún otro módulo").
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)


def set_trace_context(*, trace_id: str | None, span_id: str | None) -> None:
    """Establece el trace-id/span-id activos de la petición en curso."""
    _trace_id_var.set(trace_id)
    _span_id_var.set(span_id)


def get_trace_id() -> str | None:
    """Devuelve el trace-id activo, o ``None`` si no hay ninguna traza en curso."""
    return _trace_id_var.get()


def get_span_id() -> str | None:
    """Devuelve el span-id activo, o ``None`` si no hay ninguna traza en curso."""
    return _span_id_var.get()


#: Identidad de la petición en curso (Sprint 2.8, ver ADR-008) — mismo patrón
#: que el trace-id/span-id de arriba. ``providers/security/security_context.py``
#: (Sprint 2.7) es quien la establece, en cuanto resuelve el ``SecurityContext``
#: de cada petición — este módulo no conoce ``SecurityContext`` ni ningún tipo
#: de ``security/`` (la dirección de dependencia sigue siendo
#: ``providers/`` -> ``core/``, nunca al revés), solo guarda los dos
#: identificadores primitivos que ``JsonFormatter`` necesita para
#: enriquecer cada log (``LOGGING-STANDARD.md``, "context enrichment").
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
_tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def set_identity_context(*, user_id: str | None, tenant_id: str | None) -> None:
    """Establece el user-id/tenant-id de la identidad resuelta para la petición en curso."""
    _user_id_var.set(user_id)
    _tenant_id_var.set(tenant_id)


def get_user_id() -> str | None:
    """Devuelve el user-id de la identidad activa, o ``None`` si es anónima/no hay petición."""
    return _user_id_var.get()


def get_tenant_id() -> str | None:
    """Devuelve el tenant-id activo, o ``None`` si no aplica multi-tenant."""
    return _tenant_id_var.get()
