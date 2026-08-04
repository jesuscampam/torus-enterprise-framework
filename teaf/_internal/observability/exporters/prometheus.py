"""``PrometheusExporter`` — expone métricas en formato Prometheus (pull, no push).

Solo métricas: Prometheus no tiene noción de trazas, así que
``configure_tracing`` es intencionalmente un no-op (documentado, no un
``NotImplementedError`` — llamarlo no es un error, simplemente no hace
nada, igual que ``TracerProvider.record_metric`` en
``providers/telemetry/tracer_provider.py``, Sprint 2.2). El endpoint HTTP
``GET /metrics`` que sirve el formato de texto de Prometheus lo construye
``ObservabilityModule`` (``registry`` queda público para eso).
"""

from __future__ import annotations

from typing import Any

from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import CollectorRegistry

from teaf._internal.contracts.telemetry import Exporter


class PrometheusExporter(Exporter):
    """Reader de métricas OpenTelemetry que las publica en un ``CollectorRegistry`` propio."""

    def __init__(self, *, registry: CollectorRegistry | None = None, prefix: str = "") -> None:
        self.registry = registry or CollectorRegistry()
        self._prefix = prefix

    @property
    def name(self) -> str:
        return "prometheus"

    def configure_tracing(self, tracer_provider: Any) -> None:
        """No-op — Prometheus no exporta trazas (ver docstring del módulo)."""

    def configure_metrics(self, metric_readers: list[Any]) -> None:
        metric_readers.append(PrometheusMetricReader(prefix=self._prefix, registry=self.registry))
