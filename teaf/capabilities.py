"""``teaf.capabilities`` — el inventario de capacidades del framework.

Fachada sobre ``teaf/_internal/runtime/capabilities/`` (Sprint 2.4). ``CapabilityCategory``
se reexporta junto a ``CapabilityRegistry`` porque es imprescindible para
``ModuleBuilder.add_capability(..., category=CapabilityCategory.DATABASE)``
(``teaf.ModuleBuilder``, ver ``teaf/modules.py``) — sin él no hay forma de
categorizar una capacidad usando solo símbolos públicos.
"""

from __future__ import annotations

from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.capabilities.registry import CapabilityRegistry

__all__ = ["CapabilityCategory", "CapabilityRegistry"]
