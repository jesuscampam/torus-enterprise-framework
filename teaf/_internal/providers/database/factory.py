"""``DatabaseFactory`` — construcción desacoplada de un ``DatabaseProvider``.

Permite que el composition root (``backend/core/application.py``) obtenga
un proveedor de base de datos sin conocer su implementación concreta,
siguiendo el mismo espíritu que ``SecurityFactory`` (ver
providers/security/factory.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from teaf._internal.contracts.database import DatabaseProvider


class DatabaseFactory(ABC):
    """Construye instancias de ``DatabaseProvider``."""

    @abstractmethod
    def create(self) -> DatabaseProvider:
        """Devuelve un nuevo ``DatabaseProvider`` configurado y listo para conectar."""
        ...
