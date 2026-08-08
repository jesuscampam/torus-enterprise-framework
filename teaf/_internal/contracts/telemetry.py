"""Contratos de observabilidad (trazas, métricas, logs, exportación, salud).

``TelemetryProvider`` (Sprint 2.2) se mantiene sin cambios — sigue siendo
el contrato mínimo original. Desde Sprint 2.8 (ver ADR-008) se añaden los
contratos alrededor de los que se diseña la plataforma real:
``Tracer``/``Span`` (tracing distribuido), ``Meter``/``Counter``/
``Histogram``/``Gauge``/``UpDownCounter`` (métricas) y ``Exporter``
(destinos de telemetría) — todos implementados sobre el SDK oficial de
OpenTelemetry (nunca una abstracción propia por debajo, ver ADR-008), pero
sin filtrar tipos de ``opentelemetry.*`` en la firma de estos contratos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from teaf._internal.observability.models import SpanKind, SpanStatus


class TelemetryProvider(ABC):
    """Punto único de instrumentación de trazas y métricas."""

    @abstractmethod
    def start_span(
        self, name: str, *, attributes: dict[str, Any] | None = None
    ) -> AbstractContextManager[Any]:
        """Abre un span de traza llamado ``name``, cerrado automáticamente al salir del contexto."""
        ...

    @abstractmethod
    def record_metric(
        self, name: str, value: float, *, attributes: dict[str, Any] | None = None
    ) -> None:
        """Registra una métrica puntual (contador, gauge, etc. — lo decide la implementación)."""
        ...


class Span(ABC):
    """Un tramo de una traza distribuida — abierto por ``Tracer.start_span``."""

    @property
    @abstractmethod
    def trace_id(self) -> str:
        """Identificador (hexadecimal) de la traza completa a la que pertenece este span."""
        ...

    @property
    @abstractmethod
    def span_id(self) -> str:
        """Identificador (hexadecimal) de este span."""
        ...

    @abstractmethod
    def set_attribute(self, key: str, value: str | bool | int | float) -> None:
        """Adjunta un atributo (par clave/valor) a este span."""
        ...

    @abstractmethod
    def add_event(self, name: str, *, attributes: Mapping[str, object] | None = None) -> None:
        """Registra un evento puntual (con marca de tiempo) dentro de este span."""
        ...

    @abstractmethod
    def record_exception(self, exception: BaseException) -> None:
        """Adjunta una excepción como evento de este span y marca su estado como ``ERROR``."""
        ...

    @abstractmethod
    def set_status(self, status: SpanStatus, description: str | None = None) -> None:
        """Establece el resultado de la operación que representa este span."""
        ...


class Tracer(ABC):
    """Punto de entrada para abrir spans — el contrato central de tracing distribuido."""

    @abstractmethod
    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Mapping[str, object] | None = None,
        links: Sequence[Span] = (),
    ) -> AbstractContextManager[Span]:
        """Abre un span ``name`` (hijo del span activo, si lo hay), cerrado al salir del contexto.

        ``links`` referencia spans de otras trazas causalmente relacionados
        (p. ej. un job en background disparado por esta petición) — sin
        convertirlos en el padre directo del nuevo span.
        """
        ...


class Counter(ABC):
    """Contador monótono creciente (p. ej. peticiones totales)."""

    @abstractmethod
    def add(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None: ...


class UpDownCounter(ABC):
    """Contador que puede subir y bajar (p. ej. conexiones activas)."""

    @abstractmethod
    def add(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None: ...


class Histogram(ABC):
    """Distribución de valores puntuales (p. ej. latencia por petición)."""

    @abstractmethod
    def record(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None: ...


class Gauge(ABC):
    """Valor puntual que sube y baja libremente (p. ej. tamaño de una cola)."""

    @abstractmethod
    def set(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None: ...


class Meter(ABC):
    """Fábrica de instrumentos de métricas — el contrato central de métricas."""

    @abstractmethod
    def create_counter(self, name: str, *, unit: str = "", description: str = "") -> Counter: ...

    @abstractmethod
    def create_up_down_counter(
        self, name: str, *, unit: str = "", description: str = ""
    ) -> UpDownCounter: ...

    @abstractmethod
    def create_histogram(
        self, name: str, *, unit: str = "", description: str = ""
    ) -> Histogram: ...

    @abstractmethod
    def create_gauge(self, name: str, *, unit: str = "", description: str = "") -> Gauge: ...


class Exporter(ABC):
    """Un backend de observabilidad — sabe conectar trazas/métricas de OpenTelemetry hacia sí mismo.

    Implementado completamente para Console/OTLP/Prometheus (ver
    ``observability/exporters/``, ADR-008); Jaeger/Zipkin/Dynatrace/Elastic/
    Azure Monitor/Grafana/Datadog/New Relic/Splunk quedan preparados vía
    este mismo contrato, sin implementación concreta — todos son, en la
    práctica, alcanzables hoy vía OTLP + un Collector.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador estable de este exportador (p. ej. ``"console"``, ``"otlp"``)."""
        ...

    @abstractmethod
    def configure_tracing(self, tracer_provider: Any) -> None:
        """Conecta este exportador a un ``opentelemetry.sdk.trace.TracerProvider``."""
        ...

    @abstractmethod
    def configure_metrics(self, metric_readers: list[Any]) -> None:
        """Añade el ``MetricReader`` de este exportador (si aplica) a la lista dada."""
        ...
