"""Excepciones del Runtime.

Todas heredan de ``backend.core.exceptions.InfrastructureException`` (no se
modifica la jerarquía ya aprobada en Sprint 2.1 — se extiende por herencia,
como ya exigía esa misma jerarquía para casos de fallo de infraestructura).
"""

from __future__ import annotations

from teaf._internal.core.exceptions import InfrastructureException


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


class CapabilityNotFoundException(InfrastructureException):
    """Se pidió una capacidad (``describe``/``unregister``) que no está registrada."""

    default_error_code = "capability-not-found"


class CapabilityAlreadyRegisteredException(InfrastructureException):
    """Se intentó registrar una capacidad cuyo ``id`` ya existe en el ``CapabilityRegistry``."""

    default_error_code = "capability-already-registered"


class FeatureNotFoundException(InfrastructureException):
    """Se pidió un feature flag (``enable``/``disable``/``describe``) que no está registrado."""

    default_error_code = "feature-not-found"


class FeatureAlreadyRegisteredException(InfrastructureException):
    """Se intentó registrar un feature flag cuyo ``id`` ya existe en el ``FeatureManager``."""

    default_error_code = "feature-already-registered"
