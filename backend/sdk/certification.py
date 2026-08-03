"""``ModuleCertification`` — certifica que un módulo cumple ``ModuleSpecification v1``.

Reutiliza ``ModuleValidator.errors_by_section`` para reportar, sección por
sección, qué falló — sin reimplementar ninguna regla de validación. Las
ocho secciones de ``ModuleCertificationResult.checks`` corresponden a las
ocho que exige Sprint 2.5, ítem 15 (Specification, Manifest, Metadata,
Capabilities, Dependencies, Version, Health, Documentation).

Es deliberadamente más estricta que ``ModuleValidator`` en un punto:
exige ``documentation`` no vacía — un módulo puede ser válido para
registrarse en un ``Runtime`` (``ModuleValidator``) sin estar listo para
certificarse y distribuirse (``ModuleCertification``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from backend.sdk.module_base import ModuleBase
from backend.sdk.validator import ModuleValidator

#: Las ocho secciones certificadas, en el orden en que se reportan.
CERTIFICATION_SECTIONS: tuple[str, ...] = (
    "specification",
    "manifest",
    "metadata",
    "capabilities",
    "dependencies",
    "version",
    "health",
    "documentation",
)


@dataclass(frozen=True, slots=True)
class ModuleCertificationResult:
    """Resultado de certificar un módulo."""

    certified: bool
    checks: Mapping[str, bool]
    errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este resultado."""
        return {
            "certified": self.certified,
            "checks": dict(self.checks),
            "errors": list(self.errors),
        }


class ModuleCertification:
    """Certifica un ``ModuleBase`` contra ``ModuleSpecification v1``."""

    def __init__(self, *, validator: ModuleValidator | None = None) -> None:
        self._validator = validator or ModuleValidator()

    def certify(self, module: ModuleBase) -> ModuleCertificationResult:
        """Ejecuta las ocho verificaciones de certificación sobre ``module``."""
        manifest = module.get_manifest()
        result = self._validator.validate(manifest)
        by_section = self._validator.errors_by_section(manifest)

        checks: dict[str, bool] = {
            "specification": result.valid,
            "manifest": self._section_ok(by_section, "metadata"),
            "metadata": self._section_ok(by_section, "metadata"),
            "capabilities": self._section_ok(by_section, "capabilities"),
            "dependencies": self._section_ok(by_section, "dependencies"),
            "version": self._section_ok(by_section, "metadata"),
            "health": self._section_ok(by_section, "health"),
            "documentation": bool(manifest.descriptor.documentation),
        }

        errors = list(result.errors)
        if not checks["documentation"]:
            errors.append("documentation: falta 'documentation' — requerida para certificar.")

        return ModuleCertificationResult(
            certified=all(checks.values()), checks=checks, errors=tuple(errors)
        )

    @staticmethod
    def _section_ok(by_section: dict[str, tuple[str, ...]], section: str) -> bool:
        return section not in by_section

    @staticmethod
    def describe_sections() -> tuple[str, ...]:
        """Las secciones certificadas, para documentación/introspección."""
        return CERTIFICATION_SECTIONS
