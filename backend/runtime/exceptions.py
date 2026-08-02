"""Excepciones del Runtime.

Todas heredan de ``backend.core.exceptions.InfrastructureException`` (no se
modifica la jerarquía ya aprobada en Sprint 2.1 — se extiende por herencia,
como ya exigía esa misma jerarquía para casos de fallo de infraestructura).
"""

from __future__ import annotations

from backend.core.exceptions import InfrastructureException


class ServiceNotRegisteredException(InfrastructureException):
    """Se pidió resolver un contrato que nadie registró en el ``ServiceContainer``."""

    default_error_code = "service-not-registered"


class CircularDependencyException(InfrastructureException):
    """El ``ServiceContainer`` o el ``DependencyGraph`` detectaron un ciclo."""

    default_error_code = "circular-dependency"


class LifecycleException(InfrastructureException):
    """Un hook de ``LifecycleManager`` o un paso de ``Pipeline`` falló."""

    default_error_code = "lifecycle-error"


class PluginValidationException(InfrastructureException):
    """Un plugin no cumple el contrato mínimo exigido por ``PluginLoader``."""

    default_error_code = "plugin-validation-error"
