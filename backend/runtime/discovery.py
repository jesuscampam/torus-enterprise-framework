"""``ModuleDiscovery`` — descubre módulos registrados en el ``ModuleRegistry``.

Deliberadamente simple: en Sprint 2.3 "descubrir" significa leer el
``ModuleRegistry`` ya poblado por el composition root
(``backend/core/application.py``) — no hay escaneo de filesystem ni de
entry points (eso es responsabilidad de ``plugin_loader.py`` para plugins
externos, un mecanismo distinto y todavía sin plugins reales).
"""

from __future__ import annotations

from backend.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus


class ModuleDiscovery:
    """Lee el estado del ``ModuleRegistry`` para el resto del Runtime."""

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry

    def discover(self, *, status: ModuleStatus | None = None) -> tuple[ModuleDescriptor, ...]:
        """Devuelve los módulos registrados, opcionalmente filtrados por ``status``."""
        modules = self._registry.list_modules()
        if status is None:
            return modules
        return tuple(module for module in modules if module.status is status)
