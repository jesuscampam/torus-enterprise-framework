"""Contrato de Unit of Work (gestión de límites de transacción).

``services/`` es responsable de delimitar la transacción (ver
docs/standards/DATABASE-STANDARD.md, sección 7): ningún ``Repository``
hace commit por su cuenta. Este contrato formaliza ese límite como un
gestor de contexto asíncrono.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class UnitOfWork(ABC):
    """Delimita una transacción que puede abarcar más de un ``Repository``."""

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        """Abre la transacción y devuelve el propio Unit of Work."""
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Si hubo excepción, revierte; si no, no hace commit implícito (ver ``commit``)."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Confirma todos los cambios realizados dentro de la transacción."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Descarta todos los cambios realizados dentro de la transacción."""
        ...
