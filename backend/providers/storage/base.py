"""``BaseStorageProvider`` — clase base para implementaciones de ``StorageProvider``.

Sin lógica adicional sobre el contrato: expone únicamente su identidad
(``provider_name``), a la espera de una implementación concreta (Azure
Blob Storage u otra) en un Sprint posterior.
"""

from __future__ import annotations

from abc import ABC

from backend.contracts.storage import StorageProvider


class BaseStorageProvider(StorageProvider, ABC):
    """Base común para proveedores de almacenamiento concretos."""

    #: Nombre identificador del proveedor concreto (p. ej. "azure-blob").
    provider_name: str = "unset"
