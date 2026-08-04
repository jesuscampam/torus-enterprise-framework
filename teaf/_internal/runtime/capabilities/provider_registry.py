"""``CapabilityProviderRegistry`` — preparación para MCP (Sprint 2.4, ítem 15).

Agrega las capacidades expuestas por múltiples proveedores, el mecanismo
que un futuro servidor MCP usará para descubrir automáticamente todas las
capacidades del framework — sin implementar MCP en este Sprint.

Deliberadamente **no importa** ``backend/contracts/`` (donde vive el
contrato ``CapabilityProvider``, ver ``backend/contracts/capability_provider.py``)
para no romper la regla "Runtime nunca depende de contracts/ ni providers/"
(ver docs/runtime/RUNTIME.md). En su lugar, define un ``typing.Protocol``
estructural local: cualquier objeto con un método ``get_capabilities()``
—incluida cualquier implementación real de ``CapabilityProvider``— encaja
aquí por *duck typing*, sin herencia ni import.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CapabilityProviderLike(Protocol):
    """Forma estructural que debe cumplir cualquier proveedor de capacidades."""

    def get_capabilities(self) -> Sequence[Any]: ...


class CapabilityProviderRegistry:
    """Registro de proveedores de capacidades, agregable en una sola consulta."""

    def __init__(self) -> None:
        self._providers: dict[str, CapabilityProviderLike] = {}

    def register(self, provider_id: str, provider: CapabilityProviderLike) -> None:
        """Registra ``provider`` bajo ``provider_id``.

        Raises:
            ValueError: si ``provider_id`` ya está registrado.
        """
        if provider_id in self._providers:
            raise ValueError(f"El proveedor de capacidades '{provider_id}' ya está registrado.")
        self._providers[provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        """Elimina el proveedor ``provider_id`` si estaba registrado (idempotente)."""
        self._providers.pop(provider_id, None)

    def list_providers(self) -> tuple[str, ...]:
        """Identificadores de todos los proveedores registrados."""
        return tuple(self._providers)

    def discover_all_capabilities(self) -> tuple[Any, ...]:
        """Agrega ``get_capabilities()`` de todos los proveedores registrados.

        Este es el punto de entrada que un servidor MCP futuro llamaría para
        descubrir, de una sola vez, todas las capacidades expuestas por el
        framework — sin necesidad de conocer cada proveedor individualmente.
        """
        discovered: list[Any] = []
        for provider in self._providers.values():
            discovered.extend(provider.get_capabilities())
        return tuple(discovered)
