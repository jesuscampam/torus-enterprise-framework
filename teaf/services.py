"""``teaf.services`` — el contenedor de inyección de dependencias.

Fachada sobre ``teaf/_internal/runtime/container.py`` (Sprint 2.3). ``Lifetime`` se
reexporta junto a ``ServiceContainer`` porque es imprescindible para
``ModuleBuilder.add_service(..., lifetime=Lifetime.SCOPED)`` (``teaf.ModuleBuilder``,
ver ``teaf/modules.py``) — sin él no hay forma de declarar el ciclo de vida
de un servicio usando solo símbolos públicos.
"""

from __future__ import annotations

from teaf._internal.runtime.container import Lifetime, ServiceContainer

__all__ = ["Lifetime", "ServiceContainer"]
