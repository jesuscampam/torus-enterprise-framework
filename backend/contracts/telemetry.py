"""Contrato de telemetría (trazas, métricas y logs).

Preparado para una integración real con OpenTelemetry en un Sprint
posterior (ver docs/standards/LOGGING-STANDARD.md) — este contrato no
envía ni exporta nada, solo define la forma que tendrá el proveedor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any


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
