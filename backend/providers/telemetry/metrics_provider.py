"""``MetricsProvider`` — clase base para instrumentación de métricas."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any

from backend.contracts.telemetry import TelemetryProvider


class MetricsProvider(TelemetryProvider, ABC):
    """Base para proveedores de métricas. ``start_span`` queda para ``TracerProvider``."""

    def start_span(
        self, name: str, *, attributes: dict[str, Any] | None = None
    ) -> AbstractContextManager[Any]:
        raise NotImplementedError(
            "MetricsProvider no abre spans — usa TracerProvider (tracer_provider.py)."
        )

    @abstractmethod
    def record_metric(
        self, name: str, value: float, *, attributes: dict[str, Any] | None = None
    ) -> None: ...
