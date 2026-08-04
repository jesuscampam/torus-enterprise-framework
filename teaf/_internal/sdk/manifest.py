"""``ModuleManifest`` — el manifiesto completo y serializable de un módulo.

El equivalente TEAF a un ``package.json``/``pyproject.toml`` de un módulo:
todo lo que hace falta para identificarlo, validarlo, resolverlo y
registrarlo. Normalmente se construye con ``ModuleBuilder`` (``builder.py``),
nunca a mano — ver Sprint 2.5, ítem 4.
"""

from __future__ import annotations

from dataclasses import dataclass

from teaf._internal.sdk.capability import ModuleCapability
from teaf._internal.sdk.configuration import ModuleConfiguration
from teaf._internal.sdk.dependency import ModuleDependency
from teaf._internal.sdk.descriptor import ModuleDescriptor
from teaf._internal.sdk.health import ModuleHealth
from teaf._internal.sdk.service import ModuleService


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    """Manifiesto completo de un módulo: metadata + todo lo que aporta y necesita.

    Compone ``descriptor`` (la "Metadata" — id, name, display_name, version,
    description, author, category, tags, documentation, experimental,
    deprecated) en vez de duplicar esos campos aquí — ``as_dict()`` los
    aplana igualmente en la salida JSON.
    """

    descriptor: ModuleDescriptor
    license: str | None = None
    capabilities: tuple[ModuleCapability, ...] = ()
    dependencies: tuple[ModuleDependency, ...] = ()
    configuration: tuple[ModuleConfiguration, ...] = ()
    services: tuple[ModuleService, ...] = ()
    health_checks: tuple[ModuleHealth, ...] = ()
    #: Nombres de eventos que el módulo publica o consume en el ``EventBus``
    #: (documentación declarativa — no se suscribe nada automáticamente).
    events: tuple[str, ...] = ()
    runtime_compatibility: str = "*"
    sdk_compatibility: str = "*"

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) del manifiesto completo."""
        return {
            **self.descriptor.as_dict(),
            "license": self.license,
            "capabilities": [c.as_dict() for c in self.capabilities],
            "dependencies": [d.as_dict() for d in self.dependencies],
            "configuration": [c.as_dict() for c in self.configuration],
            "services": [s.as_dict() for s in self.services],
            "healthChecks": [h.as_dict() for h in self.health_checks],
            "events": list(self.events),
            "runtimeCompatibility": self.runtime_compatibility,
            "sdkCompatibility": self.sdk_compatibility,
        }
