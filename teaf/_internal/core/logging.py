"""Sistema de logging empresarial del framework.

Implementa docs/standards/LOGGING-STANDARD.md: logging estructurado,
correlation-id/trace-id/span-id en cada entrada, niveles configurables,
salida a consola, JSON o archivo con rotación. ``traceId``/``spanId`` son
reales desde Sprint 2.8 (ver ADR-008) — leídos de
``core/context.py::get_trace_id()``/``get_span_id()``, poblados por
``teaf._internal.observability.middleware.ObservabilityMiddleware``; antes
(Sprint 2.1-2.7) ``traceId`` era un literal ``null`` fijo, sin ningún
middleware que lo estableciera. ``userId``/``tenant`` (también Sprint 2.8)
se leen de ``core/context.py::get_user_id()``/``get_tenant_id()``, poblados
por ``providers/security/security_context.py`` en cuanto se resuelve la
identidad de la petición. ``module``/``capability`` no tienen ContextVar
propio (una misma petición puede atravesar varios) — se incluyen solo
cuando el propio log los pasa vía ``extra={"module": ..., "capability": ...}``.

Este módulo es intencionalmente independiente de ``backend/config/``: recibe
parámetros primitivos, no un objeto ``Settings``, para no introducir una
dependencia de core/ hacia config/ (ver FRAMEWORK-BLUEPRINT.md, sección 11,
regla 1 — "Core nunca depende de ningún otro módulo del framework"). Quien
conecta ``Settings`` con esta función es el composition root
(``backend/core/application.py``). Por la misma regla, la lectura de
identidad/trace/span-id se hace vía ``core/context.py`` (no
``teaf._internal.observability``/``providers/telemetry``/``providers/security``)
— ``core/`` nunca importa hacia afuera de sí mismo.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from typing import Literal

from teaf._internal.core.context import (
    NO_CORRELATION_ID,
    get_correlation_id,
    get_span_id,
    get_tenant_id,
    get_trace_id,
    get_user_id,
)

LogFormat = Literal["console", "json"]

_CONSOLE_FORMAT = "%(asctime)s %(levelname)-8s [%(correlation_id)s] %(name)s: %(message)s"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5


class CorrelationIdFilter(logging.Filter):
    """Inyecta correlation-id/trace-id/span-id/user-id/tenant-id en cada log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        record.trace_id = get_trace_id()
        record.span_id = get_span_id()
        record.user_id = get_user_id()
        record.tenant_id = get_tenant_id()
        return True


class JsonFormatter(logging.Formatter):
    """Formatea cada log record según el esquema de LOGGING-STANDARD.md sección 1.

    ``module``/``capability`` no se leen de ningún ``ContextVar`` global
    (una misma petición HTTP puede atravesar varios módulos/capacidades) —
    solo aparecen cuando el propio log los pasa explícitamente, vía
    ``extra={"module": "database", "capability": "database.query"}``.
    """

    def __init__(self, service_name: str, environment: str = "development") -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": f"{self.formatTime(record, '%Y-%m-%dT%H:%M:%S')}.{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": self._service_name,
            "environment": self._environment,
            "correlationId": getattr(record, "correlation_id", NO_CORRELATION_ID),
            "requestId": getattr(record, "correlation_id", NO_CORRELATION_ID),
            "traceId": getattr(record, "trace_id", None),
            "spanId": getattr(record, "span_id", None),
            "userId": getattr(record, "user_id", None),
            "tenant": getattr(record, "tenant_id", None),
            "message": record.getMessage(),
        }
        module = getattr(record, "module_id", None)
        if module is not None:
            payload["module"] = module
        capability = getattr(record, "capability", None)
        if capability is not None:
            payload["capability"] = capability
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        context = getattr(record, "context", None)
        if context:
            payload["context"] = context
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    *,
    level: str = "INFO",
    log_format: LogFormat = "console",
    service_name: str = "teaf-backend",
    environment: str = "development",
    log_file: str | None = None,
) -> None:
    """Configura el logger raíz del proceso.

    Args:
        level: Nivel mínimo de log (DEBUG/INFO/WARNING/ERROR/CRITICAL).
        log_format: ``"console"`` (legible en desarrollo) o ``"json"``
            (estructurado, recomendado en staging/producción).
        service_name: Nombre lógico del servicio, incluido en cada log JSON.
        environment: Entorno activo (``development``/``testing``/``staging``/
            ``production``), incluido en cada log JSON.
        log_file: Ruta de archivo opcional. Si se indica, se añade un
            handler con rotación (10 MB, 5 backups) además de la consola.
    """
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    correlation_filter = CorrelationIdFilter()
    formatter: logging.Formatter = (
        JsonFormatter(service_name, environment)
        if log_format == "json"
        else logging.Formatter(_CONSOLE_FORMAT)
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(correlation_filter)
    root.addHandler(console_handler)

    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(JsonFormatter(service_name, environment))
        file_handler.addFilter(correlation_filter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con nombre, ya sujeto a la configuración de ``configure_logging``."""
    return logging.getLogger(name)
