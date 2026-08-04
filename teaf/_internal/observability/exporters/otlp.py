"""``OtlpExporter`` — envía trazas y métricas a un OTLP Collector (HTTP) real.

El "camino universal" de ADR-008: cualquier backend con soporte OTLP
(Jaeger, Zipkin, Dynatrace, Elastic, Azure Monitor, Grafana, Datadog, New
Relic, Splunk — todos en ``prepared.py``) es alcanzable hoy mismo apuntando
este mismo exportador a su Collector, sin escribir un exportador nuevo.
"""

from __future__ import annotations

from typing import Any

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from teaf._internal.contracts.telemetry import Exporter


class OtlpExporter(Exporter):
    """Exporta vía OTLP/HTTP (protobuf) — el protocolo estándar de OpenTelemetry."""

    def __init__(
        self,
        *,
        traces_endpoint: str | None = None,
        metrics_endpoint: str | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        export_interval_millis: int = 60_000,
    ) -> None:
        self._traces_endpoint = traces_endpoint
        self._metrics_endpoint = metrics_endpoint
        self._headers = headers
        self._timeout_seconds = timeout_seconds
        self._export_interval_millis = export_interval_millis

    @property
    def name(self) -> str:
        return "otlp"

    def configure_tracing(self, tracer_provider: Any) -> None:
        exporter = OTLPSpanExporter(
            endpoint=self._traces_endpoint,
            headers=self._headers,
            timeout=self._timeout_seconds,
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

    def configure_metrics(self, metric_readers: list[Any]) -> None:
        exporter = OTLPMetricExporter(
            endpoint=self._metrics_endpoint,
            headers=self._headers,
            timeout=self._timeout_seconds,
        )
        metric_readers.append(
            PeriodicExportingMetricReader(
                exporter, export_interval_millis=self._export_interval_millis
            )
        )
