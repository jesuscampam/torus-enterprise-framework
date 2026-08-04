"""``TracerProvider`` — clase base para instrumentación de trazas."""

from __future__ import annotations

from abc import ABC
from typing import Any

from teaf._internal.contracts.telemetry import TelemetryProvider


class TracerProvider(TelemetryProvider, ABC):
    """Base para proveedores de trazas. ``record_metric`` queda para ``MetricsProvider``."""

    def record_metric(
        self, name: str, value: float, *, attributes: dict[str, Any] | None = None
    ) -> None:
        raise NotImplementedError(
            "TracerProvider no expone métricas — usa MetricsProvider (metrics_provider.py)."
        )
