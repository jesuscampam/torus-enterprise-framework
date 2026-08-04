"""``ModuleBase`` — la única clase de la que un desarrollador necesita heredar.

Un módulo TEAF completo se implementa así:

    class DemoModule(ModuleBase):
        def get_manifest(self) -> ModuleManifest:
            return (
                ModuleBuilder(id="demo", name="demo", display_name="Demo")
                .add_service(Greeter, lambda c: Greeter())
                .add_capability(id="demo.greet", name="demo-greet")
                .build()
            )

        async def ready(self, context: ModuleContext) -> None:
            context.logger.info("demo_module_ready")

``bootstrap()`` (heredado, nunca sobrescrito) hace todo lo demás: valida el
manifiesto (``ModuleValidator``), comprueba compatibilidad, registra el
módulo en el ``ModuleRegistry`` de Core, enlaza automáticamente sus
servicios y capacidades (``ServiceBinder``/``CapabilityBinder``) y ejecuta,
en orden, los siete hooks opcionales del ciclo de vida — avanzando
``self.lifecycle`` (``ModuleLifecycle``) en cada paso.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from teaf._internal.core.registry import ModuleDescriptor as CoreModuleDescriptor
from teaf._internal.core.registry import ModuleStatus as CoreModuleStatus
from teaf._internal.runtime.hooks import invoke_hook
from teaf._internal.sdk import SDK_VERSION
from teaf._internal.sdk.capability_binder import CapabilityBinder
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.exceptions import (
    ModuleCompatibilityException,
    ModuleLifecycleException,
    ModuleRegistrationException,
)
from teaf._internal.sdk.lifecycle import ModuleLifecycle, ModuleLifecycleState
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.service_binder import ServiceBinder
from teaf._internal.sdk.validator import ModuleValidator

_VERSION_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)*")
_CONSTRAINT_PATTERN = re.compile(r"^(==|>=|<=|~=|>|<)?(\d+(?:\.\d+)*)$")


def _parse_numeric_version(version: str) -> tuple[int, ...]:
    """Extrae la parte numérica inicial de ``version`` (ignora sufijos como ``-alpha``)."""
    match = _VERSION_NUMBER_PATTERN.match(version)
    if match is None:
        return (0,)
    return tuple(int(part) for part in match.group(0).split("."))


def _satisfies_constraint(actual_version: str, constraint: str) -> bool:
    """``True`` si ``actual_version`` cumple ``constraint`` (``"*"``, ``">=1.2"``, ``"1.2.3"``...).

    Solo compara la parte numérica — ``ModuleValidator`` ya garantizó que
    ``constraint`` tiene una forma reconocible antes de que esto se llame.
    """
    if constraint in ("", "*"):
        return True
    match = _CONSTRAINT_PATTERN.match(constraint)
    if match is None:
        return True
    operator = match.group(1) or "=="
    actual = _parse_numeric_version(actual_version)
    required = _parse_numeric_version(match.group(2))
    length = max(len(actual), len(required))
    actual = actual + (0,) * (length - len(actual))
    required = required + (0,) * (length - len(required))
    if operator == "==":
        return actual == required
    if operator == ">=":
        return actual >= required
    if operator == "<=":
        return actual <= required
    if operator == ">":
        return actual > required
    if operator == "<":
        return actual < required
    # "~=": compatible dentro de la misma versión menor.
    return actual[:-1] == required[:-1] and actual >= required


class ModuleBase(ABC):
    """Contrato mínimo y orquestador del ciclo de vida de un módulo TEAF."""

    def __init__(self) -> None:
        self.lifecycle = ModuleLifecycle()

    @abstractmethod
    def get_manifest(self) -> ModuleManifest:
        """Describe este módulo — la única pieza que todo módulo debe implementar."""
        ...

    # -- Hooks opcionales del ciclo de vida. Cada uno puede sobrescribirse
    # como método síncrono o ``async`` indistintamente — ``bootstrap()`` los
    # invoca con ``invoke_hook`` (``backend.runtime.hooks``), igual que
    # ``LifecycleManager``. Ninguno hace nada por defecto.

    def initialize(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Se ejecuta primero: preparar estado interno, sin tocar el Runtime todavía."""

    def configure(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Aplicar la configuración recibida en ``context.configuration``."""

    def register(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Se ejecuta tras enlazar automáticamente servicios y capacidades del módulo."""

    def start(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Arrancar cualquier recurso propio del módulo (conexiones, workers, ...)."""

    def ready(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """El módulo está completamente operativo."""

    def stop(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Detener recursos propios, en el apagado — simétrico a ``start``."""

    def dispose(self, context: ModuleContext) -> Any:  # noqa: B027 — hook opcional a propósito
        """Liberar cualquier recurso final — simétrico a ``initialize``."""

    async def bootstrap(self, context: ModuleContext) -> None:
        """Valida, registra y arranca este módulo contra ``context.runtime``.

        Orden: valida el manifiesto → comprueba compatibilidad → registra el
        módulo en ``ModuleRegistry`` → ``initialize`` → ``configure`` →
        enlaza servicios/capacidades → ``register`` → ``start`` → ``ready``.

        Raises:
            ModuleValidationException: si el manifiesto no cumple la especificación.
            ModuleCompatibilityException: si declara incompatibilidad con el Runtime/SDK actuales.
            ModuleRegistrationException: si el módulo ya estaba registrado.
            ModuleLifecycleException: si algún hook falla.
        """
        manifest = self.get_manifest()

        try:
            ModuleValidator().validate_or_raise(manifest)
            self._check_compatibility(manifest, context)

            core_descriptor = CoreModuleDescriptor(
                name=manifest.descriptor.id,
                version=manifest.descriptor.version,
                status=CoreModuleStatus.IMPLEMENTED,
                dependencies=tuple(d.module_id for d in manifest.dependencies),
                author=manifest.descriptor.author,
                description=manifest.descriptor.description,
                capabilities=tuple(c.id for c in manifest.capabilities),
                tags=manifest.descriptor.tags,
                documentation=manifest.descriptor.documentation,
                experimental=manifest.descriptor.experimental,
            )
            try:
                context.runtime.register_module(core_descriptor)
            except ValueError as exc:
                raise ModuleRegistrationException(
                    f"No se pudo registrar el módulo '{manifest.descriptor.id}': {exc}"
                ) from exc
        except Exception:
            self.lifecycle.advance(ModuleLifecycleState.FAILED)
            raise

        await self._run_stage(ModuleLifecycleState.INITIALIZED, self.initialize, context)
        await self._run_stage(ModuleLifecycleState.CONFIGURED, self.configure, context)

        ServiceBinder().bind(
            manifest.services, runtime=context.runtime, module_id=manifest.descriptor.id
        )
        CapabilityBinder().bind(
            manifest.capabilities, runtime=context.runtime, module_id=manifest.descriptor.id
        )

        await self._run_stage(ModuleLifecycleState.REGISTERED, self.register, context)
        await self._run_stage(ModuleLifecycleState.STARTED, self.start, context)
        await self._run_stage(ModuleLifecycleState.READY, self.ready, context)

    async def shutdown(self, context: ModuleContext) -> None:
        """Apaga este módulo: ``stop`` → ``dispose``, simétrico a ``bootstrap``."""
        await self._run_stage(ModuleLifecycleState.STOPPED, self.stop, context)
        await self._run_stage(ModuleLifecycleState.DISPOSED, self.dispose, context)

    def _check_compatibility(self, manifest: ModuleManifest, context: ModuleContext) -> None:
        if not _satisfies_constraint(
            context.runtime.framework_version, manifest.runtime_compatibility
        ):
            raise ModuleCompatibilityException(
                f"El módulo '{manifest.descriptor.id}' requiere runtime "
                f"'{manifest.runtime_compatibility}', pero el Runtime es "
                f"'{context.runtime.framework_version}'."
            )
        if not _satisfies_constraint(SDK_VERSION, manifest.sdk_compatibility):
            raise ModuleCompatibilityException(
                f"El módulo '{manifest.descriptor.id}' requiere SDK "
                f"'{manifest.sdk_compatibility}', pero el SDK es '{SDK_VERSION}'."
            )

    async def _run_stage(
        self,
        state: ModuleLifecycleState,
        hook: Callable[[ModuleContext], Any | Awaitable[Any]],
        context: ModuleContext,
    ) -> None:
        try:
            await invoke_hook(lambda: hook(context))
        except Exception as exc:
            self.lifecycle.advance(ModuleLifecycleState.FAILED)
            raise ModuleLifecycleException(
                f"El hook '{hook.__name__}' falló en la etapa '{state.value}': {exc}"
            ) from exc
        self.lifecycle.advance(state)
