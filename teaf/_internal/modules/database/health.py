"""``DatabaseHealth`` — adaptador síncrono sobre ``DatabaseProvider.health_check()``.

``ModuleHealth.check`` (SDK, ``backend/sdk/health.py``, Sprint 2.5) es
deliberadamente síncrono — ``Callable[[], CapabilityHealth]`` — y el SDK no
se modifica en este Sprint para admitir verificaciones asíncronas. Como
``DatabaseProvider.health_check()`` sí es ``async`` (requiere I/O de red),
``DatabaseHealth`` resuelve el desajuste con una caché en memoria:
``refresh()`` (llamado desde los hooks async de ``DatabaseModule`` —
``start``/``ready``) hace el I/O real y actualiza la caché; ``check()``
(el callable que se declara en el manifiesto) solo la lee, nunca bloquea
ni ejecuta I/O por su cuenta.
"""

from __future__ import annotations

from teaf._internal.contracts.database import DatabaseProvider
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


class DatabaseHealth:
    """Estado de salud del Database Module, con lectura síncrona y actualización async."""

    def __init__(self, provider: DatabaseProvider) -> None:
        self._provider = provider
        self._last_known = CapabilityHealth.UNKNOWN

    @property
    def last_known(self) -> CapabilityHealth:
        """Último resultado conocido, sin volver a consultar la base de datos."""
        return self._last_known

    def check(self) -> CapabilityHealth:
        """Callable síncrono compatible con ``ModuleHealth.check`` — lee la caché."""
        return self._last_known

    async def refresh(self) -> CapabilityHealth:
        """Ejecuta ``provider.health_check()`` real y actualiza la caché."""
        healthy = await self._provider.health_check()
        self._last_known = CapabilityHealth.HEALTHY if healthy else CapabilityHealth.UNHEALTHY
        return self._last_known
