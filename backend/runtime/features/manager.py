"""``FeatureManager`` — inventario y activación en tiempo de ejecución de feature flags.

Mismo espíritu que ``backend/runtime/capabilities/registry.py``: un registro
en memoria, sin persistencia, consultado por la Runtime API
(``GET /runtime/features``).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from backend.runtime.exceptions import FeatureAlreadyRegisteredException, FeatureNotFoundException
from backend.runtime.features.enums import FeatureGroup, FeatureStatus
from backend.runtime.features.flag import FeatureFlag


class FeatureManager:
    """Gestor central de feature flags del framework."""

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag) -> None:
        """Da de alta ``flag``.

        Raises:
            FeatureAlreadyRegisteredException: si ya existe un flag con el
                mismo ``id``.
        """
        if flag.id in self._flags:
            raise FeatureAlreadyRegisteredException(
                f"El feature flag '{flag.id}' ya está registrado."
            )
        self._flags[flag.id] = flag

    def enable(self, feature_id: str) -> None:
        """Activa el flag ``feature_id``.

        Raises:
            FeatureNotFoundException: si no existe.
        """
        self._set_status(feature_id, FeatureStatus.ENABLED)

    def disable(self, feature_id: str) -> None:
        """Desactiva el flag ``feature_id``.

        Raises:
            FeatureNotFoundException: si no existe.
        """
        self._set_status(feature_id, FeatureStatus.DISABLED)

    def _set_status(self, feature_id: str, status: FeatureStatus) -> None:
        flag = self.describe(feature_id)
        self._flags[feature_id] = replace(flag, status=status, updated_at=datetime.now(UTC))

    def exists(self, feature_id: str) -> bool:
        """``True`` si ``feature_id`` está registrado."""
        return feature_id in self._flags

    def is_enabled(self, feature_id: str) -> bool:
        """``True`` si ``feature_id`` está registrado y activo.

        Raises:
            FeatureNotFoundException: si no existe.
        """
        return self.describe(feature_id).status is FeatureStatus.ENABLED

    def list(self, *, group: FeatureGroup | None = None) -> tuple[FeatureFlag, ...]:
        """Todos los flags registrados, opcionalmente filtrados por ``group``."""
        values = tuple(self._flags.values())
        if group is None:
            return values
        return tuple(f for f in values if f.group is group)

    def describe(self, feature_id: str) -> FeatureFlag:
        """Devuelve el flag ``feature_id``.

        Raises:
            FeatureNotFoundException: si no existe.
        """
        flag = self._flags.get(feature_id)
        if flag is None:
            raise FeatureNotFoundException(f"El feature flag '{feature_id}' no existe.")
        return flag
