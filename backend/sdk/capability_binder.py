"""``CapabilityBinder`` — registra automáticamente las capacidades declaradas por un módulo.

Traduce cada ``ModuleCapability`` (declaración ligera, ``capability.py``) en
una ``Capability`` real (``backend.runtime.capabilities``), completando
``provider``/``module`` a partir del propio módulo, y la registra contra el
``CapabilityRegistry`` del ``Runtime`` — integración directa con Platform
Intelligence (Sprint 2.4), sin que el autor del módulo construya un
``CapabilityBuilder`` a mano (ver Sprint 2.5, ítem 8).
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.runtime.capabilities.builder import CapabilityBuilder
from backend.runtime.exceptions import CapabilityAlreadyRegisteredException
from backend.runtime.runtime import Runtime
from backend.sdk.capability import ModuleCapability
from backend.sdk.exceptions import ModuleRegistrationException


class CapabilityBinder:
    """Registra ``ModuleCapability`` contra el ``CapabilityRegistry`` de un ``Runtime``."""

    def bind(
        self, capabilities: Iterable[ModuleCapability], *, runtime: Runtime, module_id: str
    ) -> None:
        """Registra cada capacidad de ``capabilities``, con ``provider``/``module`` automáticos.

        Raises:
            ModuleRegistrationException: si alguna capacidad ya está
                registrada (mismo ``id`` que otra capacidad existente).
        """
        for module_capability in capabilities:
            builder = (
                CapabilityBuilder(id=module_capability.id, name=module_capability.name)
                .with_category(module_capability.category)
                .with_description(module_capability.description)
                .with_tags(*module_capability.tags)
                .with_provider(module_id)
                .with_module(module_id)
            )
            if module_capability.experimental:
                builder = builder.as_experimental()
            try:
                runtime.register_capability(builder.build())
            except CapabilityAlreadyRegisteredException as exc:
                raise ModuleRegistrationException(
                    f"No se pudo registrar la capacidad '{module_capability.id}' "
                    f"del módulo '{module_id}': {exc}"
                ) from exc
