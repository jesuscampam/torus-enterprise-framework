"""``PluginLoader`` — mecanismo de carga y validación de plugins.

Sin plugins reales en este Sprint (ver Sprint 2.3, "NO IMPLEMENTAR"): solo
el contrato mínimo (``Plugin``) y el mecanismo que valida y registra un
plugin candidato contra el ``ServiceContainer``. No hay descubrimiento
automático desde el filesystem ni entry points — un Sprint futuro puede
añadirlo sin cambiar este contrato.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.runtime.container import ServiceContainer
from backend.runtime.exceptions import PluginValidationException


class Plugin(ABC):
    """Contrato mínimo que debe cumplir un plugin cargable por el Runtime."""

    #: Identificador único del plugin, usado para evitar cargas duplicadas.
    name: str
    #: Versión del plugin (informativa, sin validación de formato impuesta).
    version: str

    @abstractmethod
    def register(self, container: ServiceContainer) -> None:
        """Registra en ``container`` los servicios que aporta el plugin."""
        ...


class PluginLoader:
    """Valida y carga instancias de ``Plugin`` contra un ``ServiceContainer``."""

    def __init__(self) -> None:
        self._loaded: dict[str, Plugin] = {}

    def validate(self, plugin: Plugin) -> None:
        """Verifica que ``plugin`` cumple el contrato mínimo.

        Raises:
            PluginValidationException: si falta ``name``/``version``, o si
                ya hay un plugin cargado con el mismo ``name``.
        """
        if not getattr(plugin, "name", ""):
            raise PluginValidationException("El plugin no declara un 'name' válido.")
        if not getattr(plugin, "version", ""):
            raise PluginValidationException(f"El plugin '{plugin.name}' no declara 'version'.")
        if plugin.name in self._loaded:
            raise PluginValidationException(f"El plugin '{plugin.name}' ya está cargado.")

    def load(self, plugin: Plugin, *, container: ServiceContainer) -> None:
        """Valida ``plugin`` y, si es válido, ejecuta su registro en ``container``."""
        self.validate(plugin)
        plugin.register(container)
        self._loaded[plugin.name] = plugin

    def is_loaded(self, name: str) -> bool:
        """``True`` si ya se cargó un plugin llamado ``name``."""
        return name in self._loaded

    def list_loaded(self) -> tuple[Plugin, ...]:
        """Todos los plugins cargados, en orden de carga."""
        return tuple(self._loaded.values())
