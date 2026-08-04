"""``ConsoleExporter`` — vuelca trazas y métricas a stdout (desarrollo local/diagnóstico)."""

from __future__ import annotations

from typing import Any

from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from teaf._internal.contracts.telemetry import Exporter


class ConsoleExporter(Exporter):
    """Exporta cada span/métrica a stdout en cuanto se cierra/recolecta.

    Pensado para desarrollo local — usa ``SimpleSpanProcessor`` (síncrono,
    sin lote) en vez de ``BatchSpanProcessor``, para que el span aparezca en
    consola inmediatamente, sin esperar a que se llene un buffer.
    """

    def __init__(self, *, export_interval_millis: int = 5_000) -> None:
        self._export_interval_millis = export_interval_millis

    @property
    def name(self) -> str:
        return "console"

    def configure_tracing(self, tracer_provider: Any) -> None:
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    def configure_metrics(self, metric_readers: list[Any]) -> None:
        metric_readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(), export_interval_millis=self._export_interval_millis
            )
        )
