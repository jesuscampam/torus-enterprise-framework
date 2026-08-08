"""``ModuleInspector`` — introspección de solo lectura de un ``ModuleBase``.

Mismo espíritu que el Developer API del Runtime
(``backend.developer.runtime_api.DeveloperRuntimeAPI``, Sprint 2.4), pero a
escala de un único módulo en vez de la instancia completa: responde qué
declara su ``ModuleManifest`` y en qué etapa de su ``ModuleLifecycle`` está,
sin modificar nada.
"""

from __future__ import annotations

from teaf._internal.sdk.capability import ModuleCapability
from teaf._internal.sdk.configuration import ModuleConfiguration
from teaf._internal.sdk.dependency import ModuleDependency
from teaf._internal.sdk.health import ModuleHealth
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase
from teaf._internal.sdk.service import ModuleService


class ModuleInspector:
    """Fachada de solo lectura sobre un ``ModuleBase``."""

    def __init__(self, module: ModuleBase) -> None:
        self._module = module

    def manifest(self) -> ModuleManifest:
        """El ``ModuleManifest`` declarado por el módulo."""
        return self._module.get_manifest()

    def describe(self) -> dict[str, object]:
        """El manifiesto, aplanado, más el estado actual del ``ModuleLifecycle``."""
        return {
            **self.manifest().as_dict(),
            "lifecycle": self._module.lifecycle.as_dict(),
        }

    def services(self) -> tuple[ModuleService, ...]:
        """Servicios declarados por el módulo."""
        return self.manifest().services

    def capabilities(self) -> tuple[ModuleCapability, ...]:
        """Capacidades declaradas por el módulo."""
        return self.manifest().capabilities

    def dependencies(self) -> tuple[ModuleDependency, ...]:
        """Dependencias declaradas por el módulo."""
        return self.manifest().dependencies

    def events(self) -> tuple[str, ...]:
        """Nombres de eventos que el módulo publica o consume."""
        return self.manifest().events

    def configuration(self) -> tuple[ModuleConfiguration, ...]:
        """Claves de configuración declaradas por el módulo."""
        return self.manifest().configuration

    def health(self) -> tuple[ModuleHealth, ...]:
        """Verificaciones de salud declaradas por el módulo."""
        return self.manifest().health_checks
