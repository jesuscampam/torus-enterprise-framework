"""``FeatureFlag`` — descripción de un feature flag del framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from teaf._internal.runtime.features.enums import FeatureGroup, FeatureStatus


@dataclass(frozen=True, slots=True)
class FeatureFlag:
    """Todos los datos descriptivos de un feature flag — sin comportamiento.

    Inmutable: ``FeatureManager.enable``/``disable`` no mutan la instancia,
    la reemplazan por una nueva con ``status``/``updated_at`` actualizados —
    mismo criterio que ``CapabilityMetadata`` (frozen dataclass).
    """

    id: str
    name: str
    description: str = ""
    group: FeatureGroup = FeatureGroup.PLATFORM
    status: FeatureStatus = FeatureStatus.DISABLED
    tags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este feature flag."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "group": self.group.value,
            "status": self.status.value,
            "tags": list(self.tags),
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }
