"""Excepciones del Module SDK.

``ModuleValidationException`` extiende ``ValidationException`` (los datos
de un manifiesto no cumplen una regla de validación — ver
``backend.core.exceptions``). El resto extiende ``InfrastructureException``,
igual que ``backend/runtime/exceptions.py`` — representan fallos de
infraestructura del framework al cablear un módulo, no errores de negocio.
"""

from __future__ import annotations

from backend.core.exceptions import InfrastructureException, ValidationException


class ModuleValidationException(ValidationException):
    """El ``ModuleManifest`` de un módulo no cumple la ``ModuleSpecification``."""

    default_error_code = "module-validation-error"


class ModuleCompatibilityException(InfrastructureException):
    """El módulo declara ser incompatible con el Runtime o el SDK actuales."""

    default_error_code = "module-compatibility-error"


class ModuleDependencyException(InfrastructureException):
    """Dependencia entre módulos no resoluble: ciclo, conflicto o dependencia faltante."""

    default_error_code = "module-dependency-error"


class ModuleRegistrationException(InfrastructureException):
    """Falló el registro del módulo (o alguna de sus piezas) contra el ``Runtime``."""

    default_error_code = "module-registration-error"


class ModuleLifecycleException(InfrastructureException):
    """Un hook del ciclo de vida del módulo (``initialize``, ``start``, ...) falló."""

    default_error_code = "module-lifecycle-error"
