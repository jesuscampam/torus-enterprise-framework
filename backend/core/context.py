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
