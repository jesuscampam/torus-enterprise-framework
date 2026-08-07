"""``CacheHealth`` — adaptador síncrono sobre ``CacheProvider.health_check()``.

Copia deliberada de ``DatabaseHealth`` (``modules/database/health.py``): el
``ModuleHealth.check`` del SDK es síncrono —``Callable[[], CapabilityHealth]``—
y comprobar una caché remota no lo es. La caché en memoria del último
resultado conocido resuelve el desajuste sin bloquear el hilo ni convertir
``check`` en ``async``, que rompería el contrato del SDK para todos los
módulos.
"""

from __future__ import annotations

from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


class CacheHealth:
    """Estado de salud del módulo de caché, con lectura síncrona y refresco async."""

    def __init__(self, provider: CacheProvider) -> None:
        self._provider = provider
        self._last_known = CapabilityHealth.UNKNOWN

    @property
    def last_known(self) -> CapabilityHealth:
        """Último resultado conocido, sin volver a consultar la caché."""
        return self._last_known

    def check(self) -> CapabilityHealth:
        """Callable síncrono compatible con ``ModuleHealth.check`` — lee la caché."""
        return self._last_known

    async def refresh(self) -> CapabilityHealth:
        """Ejecuta ``provider.health_check()`` real y actualiza el último resultado."""
        healthy = await self._provider.health_check()
        self._last_known = CapabilityHealth.HEALTHY if healthy else CapabilityHealth.UNHEALTHY
        return self._last_known
