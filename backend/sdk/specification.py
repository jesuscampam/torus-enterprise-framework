"""``ModuleSpecification`` — el contrato formal que todo módulo TEAF debe cumplir.

Es deliberadamente declarativa: enumera las secciones obligatorias de un
módulo (Metadata, Lifecycle, Dependencies, Capabilities, Configuration,
Services, Health, Documentation, Packaging, Validation Rules) sin
implementar las reglas en sí — esas viven en ``ModuleValidator``
(``validator.py``), que referencia esta especificación para nombrar cada
regla que aplica. Separar "qué debe cumplirse" de "cómo se comprueba" es lo
que permite versionar la especificación (``SPEC_VERSION``) sin tocar el
motor de validación.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

#: Versión de la especificación que implementa este Sprint. Sube junto con
#: cambios incompatibles a las secciones o reglas exigidas — no con cada
#: Sprint del framework.
SPEC_VERSION = "1.0"


class ModuleSpecificationSection(str, Enum):
    """Las diez secciones obligatorias de todo ``ModuleManifest``."""

    METADATA = "metadata"
    LIFECYCLE = "lifecycle"
    DEPENDENCIES = "dependencies"
    CAPABILITIES = "capabilities"
    CONFIGURATION = "configuration"
    SERVICES = "services"
    HEALTH = "health"
    DOCUMENTATION = "documentation"
    PACKAGING = "packaging"
    VALIDATION_RULES = "validation_rules"


@dataclass(frozen=True, slots=True)
class ModuleSpecification:
    """La especificación formal ``ModuleSpecification v1``.

    ``sections`` es fijo por diseño (las diez secciones definidas arriba) —
    no se parametriza por instancia; el único eje de variación entre
    especificaciones es ``version``, para permitir, en un Sprint futuro, una
    ``ModuleSpecification v2`` con secciones adicionales sin romper v1.
    """

    version: str = SPEC_VERSION
    sections: tuple[ModuleSpecificationSection, ...] = tuple(ModuleSpecificationSection)

    def describe(self) -> dict[str, object]:
        """Representación serializable (JSON) de la especificación."""
        return {
            "version": self.version,
            "sections": [section.value for section in self.sections],
        }


#: La especificación activa de este Sprint — ``ModuleValidator`` y
#: ``ModuleCertification`` la usan por defecto.
CURRENT_SPECIFICATION = ModuleSpecification()
