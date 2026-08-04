"""``RepositoryBase`` — base común para repositorios concretos.

Implementa el andamiaje compartido (guardar la sesión) sobre el contrato
``Repository`` de ``contracts/repository.py``, dejando las operaciones de
datos abstractas — equivalente formalizado del patrón ya ilustrado en
``/templates/repository-template.md``.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from teaf._internal.contracts.repository import Repository
from teaf._internal.providers.database.session import DatabaseSession

T = TypeVar("T")


class RepositoryBase(Repository[T], Generic[T]):
    """Repositorio base que opera sobre una ``DatabaseSession`` inyectada."""

    def __init__(self, session: DatabaseSession) -> None:
        self._session = session

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None: ...

    @abstractmethod
    async def list_paginated(self, *, page: int, page_size: int) -> list[T]: ...

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None: ...
