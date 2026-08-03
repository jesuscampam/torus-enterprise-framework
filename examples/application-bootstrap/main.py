"""Application Bootstrap — una Application completa con un módulo propio registrado.

Combina las dos piezas de los ejemplos anteriores: construye una
``Application`` real (la misma fachada que envolvería un servidor ASGI en
producción), arranca su ``Runtime`` y registra un módulo propio sobre él —
luego inspecciona el estado resultante.

Ejecutar:

    python examples/application-bootstrap/main.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

from teaf import (
    Application,
    CapabilityCategory,
    Lifetime,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
)


class Clock:
    """Un servicio de negocio trivial que el módulo va a exponer."""

    def now(self) -> str:
        return datetime.now(UTC).isoformat()


class ClockModule(Module):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="clock", name="clock", display_name="Clock")
            .with_version("1.0.0")
            .with_category(ModuleCategory.GENERIC)
            .add_service(Clock, lambda c: Clock(), lifetime=Lifetime.SINGLETON)
            .add_capability(id="clock.now", name="clock-now", category=CapabilityCategory.UTILITY)
            .build()
        )


async def main() -> None:
    app = Application()
    print(f"TEAF {app.version}")

    await app.runtime.startup()

    module = ClockModule()
    await module.bootstrap(ModuleContext(runtime=app.runtime, module_id="clock"))

    # ``resolve_service`` devuelve ``object`` por diseño (el Runtime no conoce
    # tipos concretos) — se sabe, por construcción, que "clock" resuelve a
    # ``Clock`` porque es el único servicio registrado bajo ese contrato.
    clock = cast(Clock, app.runtime.resolve_service(Clock))
    print(f"Hora actual: {clock.now()}")

    diagnostics = app.runtime.diagnostics()
    print(f"Módulos registrados: {diagnostics.registered_modules}")
    print(f"Servicios registrados: {diagnostics.registered_services}")
    print(f"Capacidades registradas: {diagnostics.registered_capabilities}")

    await app.runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
