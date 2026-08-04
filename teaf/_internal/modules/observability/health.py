"""``ObservabilityHealth`` — adaptador síncrono de salud del ``ObservabilityModule``.

Mismo patrón que ``modules/security/health.py``: ``check()`` (el callable
declarado en el manifiesto, ``ModuleHealth.check``) es síncrono y solo lee
una caché; ``refresh()`` es ``async`` y hace el trabajo real — aquí, sin
I/O de red propio, ``refresh()`` verifica que al menos un exportador esté
configurado (una plataforma de observabilidad sin ningún destino no está
realmente operativa, aunque no haya fallado nada).
"""

from __future__ import annotations

from collections.abc import Sequence

from teaf._internal.contracts.telemetry import Exporter
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


class ObservabilityHealth:
    """Estado de salud del ``ObservabilityModule``, con lectura síncrona y actualización async."""

    def __init__(self, exporters: Sequence[Exporter]) -> None:
        self._exporters = exporters
        self._last_known = CapabilityHealth.UNKNOWN

    @property
    def last_known(self) -> CapabilityHealth:
        """Último resultado conocido, sin volver a evaluar."""
        return self._last_known

    def check(self) -> CapabilityHealth:
        """Callable síncrono compatible con ``ModuleHealth.check`` — lee la caché."""
        return self._last_known

    async def refresh(self) -> CapabilityHealth:
        """``HEALTHY`` si hay al menos un ``Exporter`` configurado, si no ``DEGRADED``."""
        self._last_known = (
            CapabilityHealth.HEALTHY if self._exporters else CapabilityHealth.DEGRADED
        )
        return self._last_known
