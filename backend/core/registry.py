"""``ModuleRegistry`` — inventario en tiempo de ejecución de los módulos del framework.

Complementa (no sustituye) a ``docs/architecture/MODULE-CATALOG.md`` — el
catálogo documenta la intención arquitectónica; este registro refleja qué
módulos están efectivamente cableados en la instancia en ejecución, y con
qué nivel de madurez. Todo módulo futuro debe registrarse aquí durante el
arranque (ver ``backend/core/application.py``).

Permanece libre de dependencias hacia ``providers/``/``contracts/`` — solo
conoce ``str`` y un enum propio, para no romper la regla "Core nunca
depende de ningún otro módulo" (ver FRAMEWORK-BLUEPRINT.md, sección 11).

Nota de diseño: el registro se crea una vez por instancia de aplicación
(``app.state.module_registry``, ver ``backend/core/application.py``), no
como singleton de proceso — un ``lru_cache`` de proceso habría hecho que
``register()`` fallara al crear una segunda app en el mismo proceso (por
ejemplo, una app por test). El accesor inyectable vía ``Depends()`` vive
en ``backend/providers/dependencies.py`` y lee ``request.app.state``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ModuleStatus(str, Enum):
    """Nivel de madurez de un módulo registrado."""

    #: Solo existen los contratos/clases base (Sprint 2.2) — sin implementación real.
    CONTRACTS_ONLY = "contracts_only"
    #: El módulo tiene una implementación concreta funcionando.
    IMPLEMENTED = "implemented"


class ModuleLifecycleState(str, Enum):
    """Estado de ciclo de vida de un módulo, visto desde ``ModuleRegistry``.

    Deliberadamente **no** es el mismo enum que ``LifecycleStage`` de
    ``backend/runtime/lifecycle.py`` — importarlo aquí rompería la regla
    "Core nunca depende de ningún otro módulo" (ver FRAMEWORK-BLUEPRINT.md,
    sección 11). Vocabulario propio, más simple, para describir módulos —
    no el arranque completo del framework.
    """

    REGISTERED = "registered"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Identidad de un módulo registrado en el ``ModuleRegistry``.

    ``dependencies`` es aditivo desde Sprint 2.3 (Runtime): nombres de otros
    módulos registrados de los que este depende, consumidos por
    ``backend/runtime/dependency_graph.py`` para detectar ciclos antes del
    arranque. Vacío por defecto — no rompe a quien ya construía
    ``ModuleDescriptor`` sin este argumento (Sprint 2.2).

    Los campos desde ``author`` son aditivos desde Sprint 2.4 (Platform
    Intelligence): metadata descriptiva consumida por ``GET /runtime/modules``
    y por ``RuntimeSelfDescription``. Todos tienen valor por defecto — no
    rompen construcciones existentes de Sprint 2.2/2.3.
    """

    name: str
    version: str
    status: ModuleStatus
    dependencies: tuple[str, ...] = ()
    author: str | None = None
    description: str = ""
    lifecycle_state: ModuleLifecycleState = ModuleLifecycleState.REGISTERED
    capabilities: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    documentation: str | None = None
    experimental: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def id(self) -> str:
        """Alias de ``name`` — identificador estable usado por la Runtime API."""
        return self.name

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este descriptor."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "status": self.status.value,
            "lifecycleState": self.lifecycle_state.value,
            "capabilities": list(self.capabilities),
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "documentation": self.documentation,
            "experimental": self.experimental,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }


class ModuleRegistry:
    """Registro central de módulos, consultado por ``/info`` (ver monitoring/info.py)."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDescriptor] = {}

    def register(self, descriptor: ModuleDescriptor) -> None:
        """Da de alta ``descriptor``.

        Raises:
            ValueError: si ya existe un módulo registrado con el mismo nombre.
        """
        if descriptor.name in self._modules:
            raise ValueError(f"El módulo '{descriptor.name}' ya está registrado.")
        self._modules[descriptor.name] = descriptor

    def unregister(self, name: str) -> None:
        """Elimina el módulo ``name``.

        Raises:
            ValueError: si no existe un módulo registrado con ese nombre.
        """
        if name not in self._modules:
            raise ValueError(f"El módulo '{name}' no está registrado.")
        del self._modules[name]

    def get(self, name: str) -> ModuleDescriptor | None:
        """Devuelve el descriptor de ``name``, o ``None`` si no está registrado."""
        return self._modules.get(name)

    def list_modules(self) -> tuple[ModuleDescriptor, ...]:
        """Devuelve todos los módulos registrados, en orden de alta."""
        return tuple(self._modules.values())
