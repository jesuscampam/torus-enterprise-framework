"""``PluginLoader`` — mecanismo de carga y validación de plugins.

Sin plugins reales en este Sprint (ver Sprint 2.3, "NO IMPLEMENTAR"): solo
el contrato mínimo (``Plugin``) y el mecanismo que valida y registra un
plugin candidato contra el ``ServiceContainer``. No hay descubrimiento
automático desde el filesystem ni entry points — un Sprint futuro puede
añadirlo sin cambiar este contrato.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from backend.runtime.container import ServiceContainer
from backend.runtime.exceptions import PluginValidationException


class PluginLifecycleState(str, Enum):
    """Estado de ciclo de vida de un plugin, visto desde ``PluginLoader``.

    Vocabulario propio de plugins — deliberadamente distinto de
    ``ModuleLifecycleState`` (``backend/core/registry.py``): un plugin y un
    módulo son conceptos distintos aunque comparten la forma "registrado /
    activo / retirado".
    """

    REGISTERED = "registered"
    LOADED = "loaded"
    UNLOADED = "unloaded"


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Metadata descriptiva de un plugin, expuesta por ``GET /runtime/plugins``."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str | None = None
    license: str | None = None
    dependencies: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    priority: int = 0
    tags: tuple[str, ...] = ()
    compatible_runtime: str | None = None
    lifecycle: PluginLifecycleState = PluginLifecycleState.REGISTERED
    experimental: bool = False

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta metadata."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "dependencies": list(self.dependencies),
            "capabilities": list(self.capabilities),
            "priority": self.priority,
            "tags": list(self.tags),
            "compatibleRuntime": self.compatible_runtime,
            "lifecycle": self.lifecycle.value,
            "experimental": self.experimental,
        }


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

    @property
    def metadata(self) -> PluginMetadata:
        """Metadata descriptiva del plugin.

        Por defecto se deriva de ``name``/``version`` — un plugin concreto
        puede sobrescribir esta propiedad para aportar el resto de campos
        (``author``, ``capabilities``, ``tags``, etc.).
        """
        return PluginMetadata(id=self.name, name=self.name, version=self.version)


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

    def unload(self, name: str) -> None:
        """Descarga el plugin ``name``.

        Raises:
            PluginValidationException: si no hay ningún plugin cargado con
                ese ``name``.
        """
        if name not in self._loaded:
            raise PluginValidationException(f"El plugin '{name}' no está cargado.")
        del self._loaded[name]

    def is_loaded(self, name: str) -> bool:
        """``True`` si ya se cargó un plugin llamado ``name``."""
        return name in self._loaded

    def list_loaded(self) -> tuple[Plugin, ...]:
        """Todos los plugins cargados, en orden de carga."""
        return tuple(self._loaded.values())
