"""``CapabilityMetadata`` y ``Capability`` — descripción de una capacidad del framework."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from teaf._internal.runtime.capabilities.enums import (
    CapabilityCategory,
    CapabilityHealth,
    CapabilityStatus,
)


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    """Todos los datos descriptivos de una capacidad — sin comportamiento."""

    id: str
    name: str
    display_name: str
    description: str = ""
    version: str = "0.0.0"
    category: CapabilityCategory = CapabilityCategory.CUSTOM
    provider: str | None = None
    module: str | None = None
    status: CapabilityStatus = CapabilityStatus.REGISTERED
    experimental: bool = False
    deprecated: bool = False
    owner: str | None = None
    tags: tuple[str, ...] = ()
    documentation: str | None = None
    permissions_required: tuple[str, ...] = ()
    configuration_required: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    health: CapabilityHealth = CapabilityHealth.UNKNOWN
    metrics: Mapping[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta metadata."""
        return {
            "id": self.id,
            "name": self.name,
            "displayName": self.display_name,
            "description": self.description,
            "version": self.version,
            "category": self.category.value,
            "provider": self.provider,
            "module": self.module,
            "status": self.status.value,
            "experimental": self.experimental,
            "deprecated": self.deprecated,
            "owner": self.owner,
            "tags": list(self.tags),
            "documentation": self.documentation,
            "permissionsRequired": list(self.permissions_required),
            "configurationRequired": list(self.configuration_required),
            "dependencies": list(self.dependencies),
            "health": self.health.value,
            "metrics": dict(self.metrics),
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Capability:
    """Una capacidad registrada: su metadata más un ``health_check`` opcional.

    Se distingue de ``CapabilityMetadata`` (los datos) porque una capacidad
    puede, en el futuro, exponer comportamiento propio (verificar su salud
    en vivo) sin cambiar la forma de sus datos descriptivos.
    """

    metadata: CapabilityMetadata
    #: Sin uso en Sprint 2.4 (ninguna capacidad real existe todavía); listo
    #: para que un Sprint futuro conecte verificaciones de salud en vivo.
    health_check: Callable[[], CapabilityHealth] | None = None
