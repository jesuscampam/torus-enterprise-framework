"""Contrato de almacenamiento de archivos/blobs.

Ver docs/architecture/MODULE-CATALOG.md (módulo Storage, planeado para V4)
y docs/diagrams/deployment-physical.mmd (Azure Storage). Sin implementación
concreta en este Sprint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Operaciones básicas de un almacén de archivos/blobs, agnóstico de proveedor."""

    @abstractmethod
    async def upload(self, path: str, data: bytes) -> None:
        """Almacena ``data`` bajo ``path``, sobrescribiendo si ya existe."""
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Devuelve el contenido almacenado en ``path``.

        Debe lanzar ``backend.core.exceptions.InfrastructureException`` si
        ``path`` no existe.
        """
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Elimina el contenido en ``path``. Idempotente si no existe."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """``True`` si hay contenido almacenado en ``path``."""
        ...
