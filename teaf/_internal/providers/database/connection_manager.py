"""``ConnectionManager`` — clase base para implementaciones de ``DatabaseProvider``.

Añade el seguimiento de estado de conexión (``is_connected``) sobre el
contrato de ``contracts/database.py``, dejando el resto abstracto. Toda
implementación concreta futura (Sprint 2.3+) hereda de esta clase en vez
de implementar ``DatabaseProvider`` desde cero.
"""

from __future__ import annotations

from abc import abstractmethod

from teaf._internal.contracts.database import DatabaseProvider


class ConnectionManager(DatabaseProvider):
    """Base común para proveedores de base de datos: gestiona el flag de conexión."""

    def __init__(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """``True`` si ``connect()`` se ejecutó y ``disconnect()`` todavía no."""
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Las subclases deben llamar a ``self._mark_connected()`` al finalizar."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Las subclases deben llamar a ``self._mark_disconnected()`` al finalizar."""
        ...

    def _mark_connected(self) -> None:
        self._connected = True

    def _mark_disconnected(self) -> None:
        self._connected = False
