"""Contrato de proveedor de notificaciones.

Ver docs/architecture/MODULE-CATALOG.md (módulo Notifications, planeado
para V4). Sin implementación concreta en este Sprint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class NotificationChannel(str, Enum):
    """Canales de notificación soportados por el contrato."""

    EMAIL = "email"
    PUSH = "push"
    CHAT = "chat"


class NotificationProvider(ABC):
    """Envío de notificaciones a un destinatario por un canal determinado."""

    @abstractmethod
    async def send(self, *, recipient: str, message: str, channel: NotificationChannel) -> None:
        """Envía ``message`` a ``recipient`` a través de ``channel``.

        Debe lanzar ``backend.core.exceptions.InfrastructureException`` si
        el envío falla.
        """
        ...
