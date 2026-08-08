"""Contrato de proveedor de capacidades — preparación para IA/MCP (Sprint 2.4, ítem 14).

Cualquier módulo futuro que quiera anunciar sus capacidades ante el
``CapabilityProviderRegistry`` del Runtime (``backend/runtime/capabilities/provider_registry.py``)
implementa este contrato. Deliberadamente **no importa**
``backend.runtime.capabilities.metadata.Capability`` — ``contracts/`` no
depende de ``runtime/`` (igual que ``runtime/`` no depende de
``contracts/``) — por eso ``get_capabilities`` devuelve ``Sequence[Any]``:
la forma real esperada en tiempo de ejecución es la documentada en
``Capability``, pero el contrato en sí permanece desacoplado de esa clase
concreta. Sin implementación real en este Sprint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any


class CapabilityProvider(ABC):
    """Anuncia las capacidades que un módulo aporta al framework."""

    @abstractmethod
    def get_capabilities(self) -> Sequence[Any]:
        """Devuelve las capacidades expuestas por este proveedor."""
        ...
