"""``ApiAudit`` — registro de auditoría de toda petición a la API (Sprint 2.9, ADR-009).

Integrado con la plataforma de observabilidad (Sprint 2.8) por tres vías
distintas y complementarias, ninguna de las cuales sustituye a las otras:

- **Trazas**: cada registro lleva ``trace_id``/``span_id``, así que desde
  una entrada de auditoría se salta a la traza completa de esa petición.
- **Métricas**: si se le pasa un ``Meter``, ``ApiAudit`` mantiene un
  contador de peticiones auditadas y un histograma de latencias, con las
  mismas dimensiones que la auditoría.
- **Eventos**: publica ``audit.recorded`` en el ``EventBus`` del Runtime,
  para que cualquier módulo pueda reaccionar sin acoplarse a este.

Lo que **no** hace, deliberadamente: muestrear. Las trazas se muestrean
(``sampling_ratio``, ADR-008) porque son telemetría estadística; la
auditoría es un registro de cumplimiento y perder una de cada diez entradas
la invalidaría por completo.
"""

from __future__ import annotations

from collections.abc import Sequence

from teaf._internal.api.models import ApiAuditRecord, ApiOutcome, ApiRequestContext
from teaf._internal.contracts.api import AuditSink
from teaf._internal.contracts.telemetry import Counter, Histogram, Meter
from teaf._internal.core.logging import get_logger
from teaf._internal.runtime.event_bus import Event, EventBus


def build_audit_record(
    context: ApiRequestContext,
    *,
    status_code: int,
    latency_seconds: float,
    outcome: ApiOutcome = ApiOutcome.ACCEPTED,
    response_bytes: int = 0,
    api_version: str | None = None,
    reason: str | None = None,
) -> ApiAuditRecord:
    """Construye un ``ApiAuditRecord`` a partir del contexto de la petición.

    Existe para que middlewares, pruebas y código de aplicación produzcan
    registros con exactamente los mismos campos rellenados a partir del
    mismo ``ApiRequestContext``, en vez de repetir el mapeo en cada sitio.
    """
    return ApiAuditRecord(
        method=context.method,
        path=context.path,
        status_code=status_code,
        latency_seconds=latency_seconds,
        outcome=outcome,
        identity_id=context.user_id,
        tenant_id=context.tenant_id,
        api_key_id=context.api_key_id,
        client_ip=context.client_ip,
        correlation_id=context.correlation_id,
        trace_id=context.trace_id,
        span_id=context.span_id,
        api_version=api_version,
        request_bytes=context.request_bytes,
        response_bytes=response_bytes,
        reason=reason,
    )


class ApiAudit:
    """Distribuye cada ``ApiAuditRecord`` a sus destinos, métricas y eventos.

    Sin destinos configurados no falla: registra un aviso una sola vez y
    sigue publicando el evento ``audit.recorded``. Una auditoría mal
    configurada nunca debe tumbar la API que audita.
    """

    def __init__(
        self,
        sinks: Sequence[AuditSink] = (),
        *,
        event_bus: EventBus | None = None,
        meter: Meter | None = None,
        enabled: bool = True,
    ) -> None:
        self._sinks = tuple(sinks)
        #: Público y mutable a propósito: el ``EventBus`` pertenece al
        #: ``Runtime`` y solo está disponible cuando el módulo recibe su
        #: ``ModuleContext``, después de construir la auditoría (ver
        #: ``ApiProtectionModule.configure``). Mismo criterio que
        #: ``ApiGateway.event_bus``.
        self.event_bus = event_bus
        self._enabled = enabled
        self._logger = get_logger("teaf.api.audit")
        self._warned_without_sinks = False

        self._requests_total: Counter | None = None
        self._latency: Histogram | None = None
        if meter is not None:
            self._requests_total = meter.create_counter(
                "api.audit.records",
                unit="1",
                description="Peticiones registradas por la auditoría de API.",
            )
            self._latency = meter.create_histogram(
                "api.audit.latency",
                unit="s",
                description="Latencia de cada petición auditada, en segundos.",
            )

    @property
    def enabled(self) -> bool:
        """``False`` desactiva la auditoría sin desmontar el middleware."""
        return self._enabled

    @property
    def sinks(self) -> tuple[AuditSink, ...]:
        """Destinos configurados."""
        return self._sinks

    async def record(self, record: ApiAuditRecord) -> None:
        """Registra ``record`` en todos los destinos, métricas y el bus de eventos.

        Un destino que falle se registra en el log y no impide que los demás
        reciban el registro: perder una API entera porque un SIEM está caído
        sería peor que perder una entrada de auditoría en ese destino.
        """
        if not self._enabled:
            return

        if not self._sinks and not self._warned_without_sinks:
            self._logger.warning("api_audit_without_sinks")
            self._warned_without_sinks = True

        for sink in self._sinks:
            try:
                await sink.emit(record)
            except Exception as exc:  # noqa: BLE001 — ver docstring
                self._logger.error(
                    "api_audit_sink_failed",
                    extra={"context": {"sink": sink.name, "error": str(exc)}},
                )

        attributes = {
            "http.request.method": record.method,
            "http.response.status_code": record.status_code,
            "api.outcome": record.outcome.value,
        }
        if self._requests_total is not None:
            self._requests_total.add(1, attributes=attributes)
        if self._latency is not None:
            self._latency.record(record.latency_seconds, attributes=attributes)

        if self.event_bus is not None:
            self.event_bus.publish(Event(name="audit.recorded", payload=record.as_dict()))
