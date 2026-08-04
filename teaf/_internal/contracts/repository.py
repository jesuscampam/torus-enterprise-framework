"""Contrato del Repository Pattern (ver docs/standards/DATABASE-STANDARD.md).

Interfaz genérica que toda implementación concreta de acceso a datos
(SQLAlchemy u otra) deberá satisfacer. ``services/`` depende únicamente de
esta interfaz, nunca de una implementación concreta (ver
docs/architecture/ARCHITECTURE.md, principio Repository Pattern).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

#: Tipo de la entidad gestionada por el repositorio. Sin cota (bound) a
#: propósito: contracts/ no conoce ``models/`` ni ningún ORM concreto.
T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Acceso a datos para un agregado de tipo ``T``.

    Toda implementación filtra por defecto los registros dados de baja
    lógicamente (``deleted_at IS NULL``, ver DATABASE-STANDARD.md sección 4)
    y nunca realiza ``DELETE`` físico salvo excepción documentada.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Devuelve la entidad con ``entity_id``, o ``None`` si no existe (o está dada de baja)."""
        ...

    @abstractmethod
    async def list_paginated(self, *, page: int, page_size: int) -> list[T]:
        """Devuelve una página de entidades activas, ordenadas de forma determinista."""
        ...

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Registra ``entity`` para su persistencia. No hace commit — ver ``UnitOfWork``."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Marca ``entity`` como modificada para su persistencia. No hace commit."""
        ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None:
        """Da de baja lógica la entidad (``deleted_at``), nunca la elimina físicamente."""
        ...
