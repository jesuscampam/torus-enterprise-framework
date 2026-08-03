"""``ModuleDependency`` — declaración de la dependencia de un módulo sobre otro.

Consumida por ``ModuleDependencyResolver`` (``dependency_resolver.py``) para
construir el grafo de dependencias entre módulos, detectar ciclos y
conflictos de versión antes de registrar nada en el ``Runtime``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModuleDependency:
    """Dependencia declarada de un módulo sobre otro, identificado por ``module_id``.

    ``version_constraint`` es informativo en este Sprint — un literal como
    ``">=1.0.0"`` o ``"1.2.3"`` (pin exacto). ``ModuleDependencyResolver``
    solo detecta conflictos entre pines exactos distintos sobre el mismo
    ``module_id``; no implementa álgebra de rangos semver completa.
    """

    module_id: str
    version_constraint: str | None = None
    optional: bool = False

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta dependencia."""
        return {
            "moduleId": self.module_id,
            "versionConstraint": self.version_constraint,
            "optional": self.optional,
        }
