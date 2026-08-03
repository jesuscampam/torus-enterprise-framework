"""``LoggerProvider`` — puente futuro entre logging y OpenTelemetry.

No sustituye a ``backend/core/logging.py`` (que sigue siendo el logging
estándar del framework, ver Sprint 2.1); esta clase es el contrato que un
exportador de logs hacia OpenTelemetry deberá implementar más adelante,
sin conectarse todavía.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoggerProvider(ABC):
    """Puente abstracto entre el logging del framework y un backend de observabilidad."""

    @abstractmethod
    def get_logger(self, name: str) -> Any:
        """Devuelve un logger correlacionado con el backend de observabilidad configurado."""
        ...
