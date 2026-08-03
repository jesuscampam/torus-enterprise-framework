"""Flujo completo de autoría de un módulo usando exclusivamente `from teaf import ...`.

Es la prueba central de que la API pública es genuinamente usable de
extremo a extremo (construir, describir, registrar, resolver) — no solo
que cada símbolo se puede importar de forma aislada.
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


class _Greeter:
    def hello(self) -> str:
        return "hi"


class _GreeterModule(Module):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="greeter", name="greeter", display_name="Greeter")
            .with_version("1.0.0")
            .with_category(ModuleCategory.GENERIC)
            .add_service(_Greeter, lambda c: _Greeter(), lifetime=Lifetime.SINGLETON)
            .add_capability(
                id="greeter.hello", name="greeter-hello", category=CapabilityCategory.UTILITY
            )
            .add_healthcheck(name="greeter.ping", check=lambda: Health.HEALTHY)
            .build()
        )


async def _bootstrap_and_inspect() -> tuple[str, bool, bool]:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.6.1-alpha")
    await runtime.startup()

    module = _GreeterModule()
    await module.bootstrap(ModuleContext(runtime=runtime, module_id="greeter"))

    greeter = cast(_Greeter, runtime.resolve_service(_Greeter))
    capability_registered = runtime.capability_registry.exists("greeter.hello")
    module_registered = any(m.name == "greeter" for m in runtime.modules)

    await runtime.shutdown()
    return greeter.hello(), capability_registered, module_registered


def test_module_authored_with_teaf_only_bootstraps_against_a_real_runtime() -> None:
    greeting, capability_registered, module_registered = asyncio.run(_bootstrap_and_inspect())
    assert greeting == "hi"
    assert capability_registered is True
    assert module_registered is True


def test_module_is_a_teaf_module_instance() -> None:
    module = _GreeterModule()
    assert isinstance(module, Module)
