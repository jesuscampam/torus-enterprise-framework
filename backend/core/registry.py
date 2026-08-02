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

from dataclasses import dataclass
from enum import Enum


class ModuleStatus(str, Enum):
    """Nivel de madurez de un módulo registrado."""

    #: Solo existen los contratos/clases base (Sprint 2.2) — sin implementación real.
    CONTRACTS_ONLY = "contracts_only"
    #: El módulo tiene una implementación concreta funcionando.
    IMPLEMENTED = "implemented"


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Identidad de un módulo registrado en el ``ModuleRegistry``.

    ``dependencies`` es aditivo desde Sprint 2.3 (Runtime): nombres de otros
    módulos registrados de los que este depende, consumidos por
    ``backend/runtime/dependency_graph.py`` para detectar ciclos antes del
    arranque. Vacío por defecto — no rompe a quien ya construía
    ``ModuleDescriptor`` sin este argumento (Sprint 2.2).
    """

    name: str
    version: str
    status: ModuleStatus
    dependencies: tuple[str, ...] = ()


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

    def get(self, name: str) -> ModuleDescriptor | None:
        """Devuelve el descriptor de ``name``, o ``None`` si no está registrado."""
        return self._modules.get(name)

    def list_modules(self) -> tuple[ModuleDescriptor, ...]:
        """Devuelve todos los módulos registrados, en orden de alta."""
        return tuple(self._modules.values())
