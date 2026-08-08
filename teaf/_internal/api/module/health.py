"""``ApiProtectionHealth`` — adaptador síncrono de salud del ``ApiProtectionModule``.

Mismo patrón que ``modules/security/health.py`` y
``modules/observability/health.py``: ``check()`` (el callable declarado en el
manifiesto) es síncrono y solo lee una caché; ``refresh()`` es ``async`` y
hace el trabajo real.

Qué se considera saludable aquí: que la cadena de protección tenga al menos
un middleware activo. Una plataforma de protección sin nada que aplicar no
está "rota" —no ha fallado nada— pero tampoco está protegiendo, así que se
reporta ``DEGRADED``: es información que el operador necesita ver en
``/health`` antes de descubrirla en un incidente.
"""

from __future__ import annotations

from teaf._internal.api.gateway.gateway import ApiGateway
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


class ApiProtectionHealth:
    """Estado de salud del ``ApiProtectionModule``, con lectura síncrona y refresco async."""

    def __init__(self, gateway: ApiGateway) -> None:
        self._gateway = gateway
        self._last_known = CapabilityHealth.UNKNOWN

    @property
    def last_known(self) -> CapabilityHealth:
        """Último resultado conocido, sin volver a evaluar."""
        return self._last_known

    def check(self) -> CapabilityHealth:
        """Callable síncrono compatible con ``ModuleHealth.check`` — lee la caché."""
        return self._last_known

    async def refresh(self) -> CapabilityHealth:
        """``HEALTHY`` si hay alguna protección activa, si no ``DEGRADED``."""
        self._last_known = (
            CapabilityHealth.HEALTHY
            if self._gateway.enabled_middlewares
            else CapabilityHealth.DEGRADED
        )
        return self._last_known
