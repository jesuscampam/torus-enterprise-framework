"""``SecretProvider`` — interfaz abstracta para gestión de secretos.

Patrón similar a ``CacheProvider`` (ADR-012): desacoplamiento de implementación.
Permite reemplazar fuente de secretos (env vars hoy, Vault/Azure Key Vault mañana)
sin cambiar la app.

Cada secreto se accede por clave: ``provider.get("db_password", default=None)``
Returns el valor o `default` si no existe (graceful degradation).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SecretProvider(ABC):
    """Interfaz abstracta para leer secretos de cualquier fuente."""

    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """Obtener valor de secreto por clave.

        Args:
            key: Identificador del secreto (ej: "db_password", "jwt_secret")
            default: Valor por defecto si no existe

        Returns:
            Valor del secreto o `default` si no existe

        Raises:
            SecretNotFoundError: Si secret no existe y no hay default
        """
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Guardar secreto (solo si el provider lo soporta).

        Args:
            key: Identificador del secreto
            value: Valor a guardar

        Raises:
            NotImplementedError: Si el provider no soporta escritura
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Borrar secreto (solo si el provider lo soporta).

        Args:
            key: Identificador del secreto

        Raises:
            NotImplementedError: Si el provider no soporta borrado
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nombre identificador del proveedor (ej: "env_vars", "vault", "azure")."""
        ...
