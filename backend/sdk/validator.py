"""``ModuleValidator`` — motor de validación de un ``ModuleManifest`` contra su especificación.

Cada método privado ``_check_*`` corresponde a una sección de
``ModuleSpecificationSection`` (``specification.py``) — la especificación
declara *qué* secciones existen, este motor implementa *cómo* se valida
cada una. Sin validación de rangos semver completos ni resolución de
paquetes reales (eso es ``ModuleDependencyResolver``, ver
``dependency_resolver.py``) — aquí solo se valida la forma de un manifiesto
individual, no las relaciones entre varios.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.sdk.exceptions import ModuleValidationException
from backend.sdk.manifest import ModuleManifest

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]*$")
_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
_COMPATIBILITY_PATTERN = re.compile(r"^(\*|(==|>=|<=|~=|>|<)?\d+\.\d+(\.\d+)?)$")


@dataclass(frozen=True, slots=True)
class ModuleValidationResult:
    """Resultado de validar un ``ModuleManifest``."""

    valid: bool
    errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este resultado."""
        return {"valid": self.valid, "errors": list(self.errors)}


class ModuleValidator:
    """Valida un ``ModuleManifest`` contra las reglas de ``ModuleSpecification v1``."""

    def validate(self, manifest: ModuleManifest) -> ModuleValidationResult:
        """Ejecuta todas las reglas y devuelve el resultado agregado (nunca lanza)."""
        errors: list[str] = []
        errors.extend(self._check_metadata(manifest))
        errors.extend(self._check_dependencies(manifest))
        errors.extend(self._check_capabilities(manifest))
        errors.extend(self._check_configuration(manifest))
        errors.extend(self._check_services(manifest))
        errors.extend(self._check_health(manifest))
        errors.extend(self._check_packaging(manifest))
        return ModuleValidationResult(valid=not errors, errors=tuple(errors))

    def errors_by_section(self, manifest: ModuleManifest) -> dict[str, tuple[str, ...]]:
        """Como ``validate``, pero agrupa los errores por sección (prefijo antes de ``:``).

        Usado por ``ModuleCertification`` (``certification.py``) para reportar
        qué sección de la especificación falló, sin volver a implementar las
        reglas de validación.
        """
        grouped: dict[str, list[str]] = {}
        for error in self.validate(manifest).errors:
            section, _, _ = error.partition(":")
            grouped.setdefault(section, []).append(error)
        return {section: tuple(errors) for section, errors in grouped.items()}

    def validate_or_raise(self, manifest: ModuleManifest) -> None:
        """Como ``validate``, pero lanza si el resultado no es válido.

        Raises:
            ModuleValidationException: con todos los errores encontrados,
                unidos en un solo mensaje.
        """
        result = self.validate(manifest)
        if not result.valid:
            raise ModuleValidationException(
                f"El manifiesto de '{manifest.descriptor.id}' no es válido: "
                + "; ".join(result.errors)
            )

    def _check_metadata(self, manifest: ModuleManifest) -> list[str]:
        errors: list[str] = []
        descriptor = manifest.descriptor
        if not descriptor.id or not _SLUG_PATTERN.match(descriptor.id):
            errors.append(
                f"metadata: 'id' inválido ('{descriptor.id}') — debe ser un slug en "
                "minúsculas (letras, dígitos, '.', '-', '_')."
            )
        if not descriptor.name:
            errors.append("metadata: 'name' no puede estar vacío.")
        if not descriptor.display_name:
            errors.append("metadata: 'display_name' no puede estar vacío.")
        if not _VERSION_PATTERN.match(descriptor.version):
            errors.append(
                f"metadata: 'version' inválida ('{descriptor.version}') — debe ser semver "
                "(p. ej. '1.0.0' o '1.0.0-alpha')."
            )
        return errors

    def _check_dependencies(self, manifest: ModuleManifest) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for dependency in manifest.dependencies:
            if dependency.module_id == manifest.descriptor.id:
                errors.append(f"dependencies: '{dependency.module_id}' depende de sí mismo.")
            if dependency.module_id in seen:
                errors.append(f"dependencies: '{dependency.module_id}' declarado más de una vez.")
            seen.add(dependency.module_id)
        return errors

    def _check_capabilities(self, manifest: ModuleManifest) -> list[str]:
        seen: set[str] = set()
        errors: list[str] = []
        for capability in manifest.capabilities:
            if capability.id in seen:
                errors.append(f"capabilities: id duplicado '{capability.id}'.")
            seen.add(capability.id)
        return errors

    def _check_configuration(self, manifest: ModuleManifest) -> list[str]:
        seen: set[str] = set()
        errors: list[str] = []
        for entry in manifest.configuration:
            if entry.key in seen:
                errors.append(f"configuration: clave duplicada '{entry.key}'.")
            seen.add(entry.key)
        return errors

    def _check_services(self, manifest: ModuleManifest) -> list[str]:
        seen: set[type] = set()
        errors: list[str] = []
        for service in manifest.services:
            if service.contract in seen:
                errors.append(f"services: contrato duplicado '{service.contract.__name__}'.")
            seen.add(service.contract)
        return errors

    def _check_health(self, manifest: ModuleManifest) -> list[str]:
        seen: set[str] = set()
        errors: list[str] = []
        for health_check in manifest.health_checks:
            if not health_check.name:
                errors.append("health: un healthcheck no puede tener 'name' vacío.")
            if health_check.name in seen:
                errors.append(f"health: nombre duplicado '{health_check.name}'.")
            seen.add(health_check.name)
        return errors

    def _check_packaging(self, manifest: ModuleManifest) -> list[str]:
        errors: list[str] = []
        if not _COMPATIBILITY_PATTERN.match(manifest.runtime_compatibility):
            errors.append(
                "packaging: 'runtime_compatibility' inválida "
                f"('{manifest.runtime_compatibility}')."
            )
        if not _COMPATIBILITY_PATTERN.match(manifest.sdk_compatibility):
            errors.append(
                f"packaging: 'sdk_compatibility' inválida ('{manifest.sdk_compatibility}')."
            )
        return errors
