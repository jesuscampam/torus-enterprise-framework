"""``DatabaseSession`` — unidad de interacción con la base de datos.

Forma abstracta de lo que en una implementación concreta será una sesión
de SQLAlchemy 2.x (``AsyncSession``); ``providers/`` no importa SQLAlchemy
todavía (ver Sprint 2.2, "NO IMPLEMENTAR").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DatabaseSession(ABC):
    """Sesión de base de datos con alcance de una unidad de trabajo."""

    @abstractmethod
    async def execute(self, statement: Any) -> Any:
        """Ejecuta ``statement`` contra la base de datos y devuelve su resultado."""
        ...

    @abstractmethod
    async def flush(self) -> None:
        """Envía los cambios pendientes a la base de datos sin confirmar la transacción."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Libera los recursos de la sesión."""
        ...
