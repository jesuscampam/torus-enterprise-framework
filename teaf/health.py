"""``teaf.health`` — el vocabulario de salud compartido por módulos, capacidades y servicios.

``Health`` es un alias de ``CapabilityHealth`` (``teaf/_internal/runtime/capabilities/enums.py``,
Sprint 2.4) — el mismo enum de cuatro valores (``UNKNOWN``/``HEALTHY``/
``DEGRADED``/``UNHEALTHY``) que ya usan internamente ``ModuleHealth.check``
(``ModuleBuilder.add_healthcheck``, ver ``teaf/modules.py``) y
``CapabilityMetadata.health``. Un nombre corto y neutral en la superficie
pública, en vez de obligar a un autor de módulos a saber que "capacidad" es
el término interno correcto.
"""

from __future__ import annotations

from teaf._internal.runtime.capabilities.enums import CapabilityHealth

#: Alias público de ``CapabilityHealth`` — ver docstring del módulo.
Health = CapabilityHealth

__all__ = ["Health"]
