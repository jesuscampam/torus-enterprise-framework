"""``SecurityHealth`` — adaptador síncrono de salud del ``SecurityModule``.

Mismo patrón que ``modules/database/health.py``: ``check()`` (el callable
declarado en el manifiesto, ``ModuleHealth.check``) es síncrono y solo lee
una caché; ``refresh()`` es ``async`` y hace el trabajo real — aquí, sin
I/O de red (JWT/API Key son en memoria), ``refresh()`` solo verifica que
el registro de proveedores tenga al menos uno registrado.
"""

from __future__ import annotations

from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.security.identity_providers.registry import IdentityProviderRegistry


class SecurityHealth:
    """Estado de salud del ``SecurityModule``, con lectura síncrona y actualización async."""

    def __init__(self, provider_registry: IdentityProviderRegistry) -> None:
        self._provider_registry = provider_registry
        self._last_known = CapabilityHealth.UNKNOWN

    @property
    def last_known(self) -> CapabilityHealth:
        """Último resultado conocido, sin volver a evaluar."""
        return self._last_known

    def check(self) -> CapabilityHealth:
        """Callable síncrono compatible con ``ModuleHealth.check`` — lee la caché."""
        return self._last_known

    async def refresh(self) -> CapabilityHealth:
        """``HEALTHY`` si hay al menos un ``IdentityProvider`` registrado, si no ``DEGRADED``."""
        self._last_known = (
            CapabilityHealth.HEALTHY
            if self._provider_registry.providers
            else CapabilityHealth.DEGRADED
        )
        return self._last_known
