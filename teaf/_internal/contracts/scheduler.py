"""Contrato de proveedor de tareas programadas.

Ver backend/scheduler/README.md y docs/architecture/MODULE-CATALOG.md
(módulo Scheduler, coordinado multi-instancia, planeado para V4). Sin
implementación concreta en este Sprint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


class SchedulerProvider(ABC):
    """Programación de trabajos recurrentes y diferidos."""

    @abstractmethod
    def schedule(
        self, job: Callable[[], Awaitable[Any]], *, cron_expression: str, job_id: str
    ) -> None:
        """Registra ``job`` para ejecutarse según ``cron_expression``, con id ``job_id``."""
        ...

    @abstractmethod
    def run_once(
        self, job: Callable[[], Awaitable[Any]], *, delay_seconds: float, job_id: str
    ) -> None:
        """Registra ``job`` para ejecutarse una única vez tras ``delay_seconds``."""
        ...

    @abstractmethod
    def cancel(self, job_id: str) -> None:
        """Cancela el job ``job_id`` si todavía no se ejecutó."""
        ...
