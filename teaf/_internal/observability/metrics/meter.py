"""``OtelMeter`` y sus instrumentos — implementación de ``Meter`` sobre OpenTelemetry.

Los cuatro instrumentos síncronos que expone ``Meter`` (``Counter``,
``UpDownCounter``, ``Histogram``, ``Gauge``) cubren tanto métricas de
negocio (p. ej. ``orders_created_total``) como de framework/runtime (p. ej.
``http_request_duration_seconds``, ver ``observability/middleware.py``).
Los instrumentos *observable* (asíncronos, con callback) de OpenTelemetry
no se envuelven aquí — un consumidor que los necesite construye
directamente sobre ``opentelemetry.metrics`` (``Meter`` no lo impide, solo
no lo reexpone).
"""

from __future__ import annotations

from collections.abc import Mapping

from opentelemetry import metrics as otel_metrics

from teaf._internal.contracts.telemetry import Counter, Gauge, Histogram, Meter, UpDownCounter


class OtelCounter(Counter):
    def __init__(self, counter: otel_metrics.Counter) -> None:
        self._counter = counter

    def add(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None:
        self._counter.add(value, attributes=dict(attributes) if attributes else None)


class OtelUpDownCounter(UpDownCounter):
    def __init__(self, counter: otel_metrics.UpDownCounter) -> None:
        self._counter = counter

    def add(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None:
        self._counter.add(value, attributes=dict(attributes) if attributes else None)


class OtelHistogram(Histogram):
    def __init__(self, histogram: otel_metrics.Histogram) -> None:
        self._histogram = histogram

    def record(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None:
        self._histogram.record(value, attributes=dict(attributes) if attributes else None)


class OtelGauge(Gauge):
    def __init__(self, gauge: otel_metrics.Gauge) -> None:
        self._gauge = gauge

    def set(self, value: float, *, attributes: Mapping[str, object] | None = None) -> None:
        self._gauge.set(value, attributes=dict(attributes) if attributes else None)


class OtelMeter(Meter):
    """Envuelve un ``opentelemetry.metrics.Meter`` real."""

    def __init__(self, meter: otel_metrics.Meter) -> None:
        self._meter = meter

    def create_counter(self, name: str, *, unit: str = "", description: str = "") -> Counter:
        return OtelCounter(self._meter.create_counter(name, unit=unit, description=description))

    def create_up_down_counter(
        self, name: str, *, unit: str = "", description: str = ""
    ) -> UpDownCounter:
        return OtelUpDownCounter(
            self._meter.create_up_down_counter(name, unit=unit, description=description)
        )

    def create_histogram(self, name: str, *, unit: str = "", description: str = "") -> Histogram:
        return OtelHistogram(self._meter.create_histogram(name, unit=unit, description=description))

    def create_gauge(self, name: str, *, unit: str = "", description: str = "") -> Gauge:
        return OtelGauge(self._meter.create_gauge(name, unit=unit, description=description))
