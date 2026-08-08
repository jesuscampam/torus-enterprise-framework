"""Exportadores preparados — contrato cumplido, sin conectividad propia (ver ADR-008).

Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog, New
Relic y Splunk son, todos, backends con soporte OTLP nativo — TEAF no
reimplementa un exportador propietario por backend cuando
``OtlpExporter`` (``otlp.py``) ya resuelve la conectividad real hacia
cualquiera de ellos apuntando al Collector/endpoint correcto. Estas clases
existen para que ``name`` sea un identificador estable y descubrible desde
código (``teaf.observability`` los expone) sin forzar a quien las
instancie a saber de antemano que debe usar ``OtlpExporter`` en su lugar —
lo descubre en el primer uso, vía el mensaje de ``NotImplementedError``.

Añadir soporte nativo real a cualquiera de ellos en el futuro es aditivo:
implementar ``configure_tracing``/``configure_metrics`` en la subclase
correspondiente no requiere tocar ``Exporter`` ni ningún otro exportador.
"""

from __future__ import annotations

from typing import Any

from teaf._internal.contracts.telemetry import Exporter


class PreparedExporter(Exporter):
    """Base de un exportador con contrato cumplido pero sin implementación de conectividad."""

    #: Nombre estable del exportador — cada subclase lo redefine.
    _NAME = "prepared"

    @property
    def name(self) -> str:
        return self._NAME

    def _not_implemented(self) -> NotImplementedError:
        return NotImplementedError(
            f"El exportador '{self.name}' está preparado (contrato Exporter cumplido) pero sin "
            f"conectividad nativa implementada todavía — usa OtlpExporter "
            f"(teaf.observability.OtlpExporter) apuntando al Collector/endpoint OTLP de "
            f"'{self.name}', o implementa este exportador de forma nativa (ver ADR-008)."
        )

    def configure_tracing(self, tracer_provider: Any) -> None:
        raise self._not_implemented()

    def configure_metrics(self, metric_readers: list[Any]) -> None:
        raise self._not_implemented()


class JaegerExporter(PreparedExporter):
    _NAME = "jaeger"


class ZipkinExporter(PreparedExporter):
    _NAME = "zipkin"


class DynatraceExporter(PreparedExporter):
    _NAME = "dynatrace"


class ElasticExporter(PreparedExporter):
    _NAME = "elastic"


class AzureMonitorExporter(PreparedExporter):
    _NAME = "azure-monitor"


class GrafanaExporter(PreparedExporter):
    _NAME = "grafana"


class DatadogExporter(PreparedExporter):
    _NAME = "datadog"


class NewRelicExporter(PreparedExporter):
    _NAME = "new-relic"


class SplunkExporter(PreparedExporter):
    _NAME = "splunk"
