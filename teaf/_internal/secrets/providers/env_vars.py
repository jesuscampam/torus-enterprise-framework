"""``EnvVarsProvider`` — implementación base usando variables de entorno.

Lee secretos desde `os.environ` y `.env` (vía python-dotenv si está disponible).
Soporta lectura; escritura es un no-op (los valores son estáticos en env).

**Uso en v1.0-beta**: proveedor predeterminado hasta que Vault entre en v1.0.1.
"""

from __future__ import annotations

import logging
import os
from typing import ClassVar

from teaf._internal.secrets.provider import SecretProvider

logger = logging.getLogger(__name__)


class EnvVarsProvider(SecretProvider):
    """Lee secretos de `os.environ` (incluyendo `.env` si python-dotenv está disponible)."""

    provider_name_value: ClassVar[str] = "env_vars"

    def __init__(self) -> None:
        """Inicializa proveedor: intenta cargar `.env` si python-dotenv está disponible."""
        self._load_env_file()

    @staticmethod
    def _load_env_file() -> None:
        """Carga `.env` si existe y python-dotenv está disponible."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            # python-dotenv no está instalado, usar solo os.environ
            logger.debug("python-dotenv not installed; using os.environ only")

    def get(self, key: str, default: str | None = None) -> str | None:
        """Obtener valor de `os.environ`.

        Args:
            key: Variable de entorno (ej: "DATABASE_URL", "JWT_SECRET")
            default: Valor si no existe

        Returns:
            Valor de os.environ o `default`
        """
        return os.environ.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Guardar en `os.environ` (solo para sesión actual).

        No persiste a `.env` file. Útil para testing.

        Args:
            key: Variable de entorno
            value: Valor
        """
        os.environ[key] = value
        # `extra={"context": {...}}` es la convención de logging estructurado del
        # framework (ver LOGGING-STANDARD.md). Pasar los campos como kwargs
        # sueltos hacía estallar `Logger._log` con TypeError en cuanto el nivel
        # DEBUG estaba activo — que es el de por defecto en desarrollo.
        logger.debug(
            "secret_set_in_memory",
            extra={"context": {"key": key, "provider": self.provider_name_value}},
        )

    def delete(self, key: str) -> None:
        """Borrar de `os.environ`.

        No persiste. Útil para testing.

        Args:
            key: Variable de entorno
        """
        os.environ.pop(key, None)
        logger.debug(
            "secret_deleted_from_memory",
            extra={"context": {"key": key, "provider": self.provider_name_value}},
        )

    @property
    def provider_name(self) -> str:
        """Nombre del proveedor."""
        return self.provider_name_value
