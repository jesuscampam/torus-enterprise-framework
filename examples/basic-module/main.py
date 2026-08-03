"""Basic Module — construir un módulo TEAF propio y registrarlo contra un Runtime.

Demuestra el flujo completo de autoría de módulos usando solo símbolos
públicos: heredar de ``Module``, describirlo con ``ModuleBuilder``, y
dejar que ``bootstrap()`` lo registre automáticamente — nunca se llama a
mano a ningún registro interno.

Ejecutar:

    python examples/basic-module/main.py
"""

from __future__ import annotations

import asyncio
from typing import cast

from teaf import (
    CapabilityCategory,
    Health,
    Lifetime,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
    ModuleRegistry,
    Runtime,
)


class Greeter:
    """Un servicio de negocio trivial que el módulo va a exponer."""

    def greet(self, name: str) -> str:
        return f"Hola, {name}."


class GreeterModule(Module):
    """Un módulo mínimo: un servicio, una capacidad, un healthcheck."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="greeter", name="greeter", display_name="Greeter")
            .with_version("1.0.0")
            .with_description("Ejemplo mínimo de módulo TEAF.")
            .with_category(ModuleCategory.GENERIC)
            .add_service(Greeter, lambda c: Greeter(), lifetime=Lifetime.SINGLETON)
            .add_capability(
                id="greeter.greet",
                name="greeter-greet",
                category=CapabilityCategory.UTILITY,
                description="Saluda por nombre.",
            )
            .add_healthcheck(name="greeter.ping", check=lambda: Health.HEALTHY)
            .build()
        )

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info("greeter_module_ready")


async def main() -> None:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.6.1-alpha")
    await runtime.startup()

    module = GreeterModule()
    await module.bootstrap(ModuleContext(runtime=runtime, module_id="greeter"))

    # ``resolve_service`` devuelve ``object`` por diseño (el Runtime no conoce
    # tipos concretos) — se sabe, por construcción, que "greeter" resuelve a
    # ``Greeter`` porque es el único servicio registrado bajo ese contrato.
    greeter = cast(Greeter, runtime.resolve_service(Greeter))
    print(greeter.greet("TEAF"))
    print(f"Capacidad registrada: {runtime.capability_registry.exists('greeter.greet')}")

    await runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
