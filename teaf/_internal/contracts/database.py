"""Contrato de proveedor de base de datos.

Abstrae el ciclo de vida de la conexión a la base de datos (motor, pool,
sesión) detrás de una interfaz independiente del driver/ORM concreto —
preparado para SQLAlchemy 2.x (ver docs/architecture/STACK.md) sin acoplar
``contracts/`` a esa librería.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DatabaseProvider(ABC):
    """Ciclo de vida de la conexión a base de datos."""

    @abstractmethod
    async def connect(self) -> None:
        """Establece el pool de conexiones. Idempotente si ya está conectado."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cierra el pool de conexiones de forma ordenada."""
        ...

    @abstractmethod
    def get_session(self) -> Any:
        """Devuelve una nueva sesión/unidad de trabajo contra la base de datos.

        El tipo de retorno concreto lo define la implementación (por
        ejemplo, ``AsyncSession`` de SQLAlchemy); ``contracts/`` no importa
        ningún ORM, de ahí el tipo ``Any``.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """``True`` si la base de datos responde; usado por ``/ready`` en el futuro."""
        ...
