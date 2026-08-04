"""Module Registration API — registrar módulos usando exclusivamente ``teaf.Application``.

Demuestra la forma más simple de arrancar un módulo (Sprint 2.6.3): se pasa
al construir la ``Application``, y arranca solo cuando arranca el ciclo de
vida de la aplicación — sin ``bootstrap()`` manual, sin threads, sin
``asyncio.run()``. ``TestClient`` (la misma herramienta que usan las
pruebas del framework) es lo que dispara ese ciclo de vida de forma
síncrona desde un script — nunca hace falta gestionar un event loop a mano.

Ejecutar:

    python examples/module-registration/main.py
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from teaf import (
    Application,
    CapabilityCategory,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleManifest,
)


class HelloModule(Module):
    """Un módulo mínimo: solo describe su manifiesto — nada más."""

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="hello", name="hello", display_name="Hello")
            .with_version("1.0.0")
            .with_category(ModuleCategory.GENERIC)
            .add_capability(
                id="hello.greet", name="hello-greet", category=CapabilityCategory.UTILITY
            )
            .build()
        )


# Opción A: pasar los módulos al construir la Application.
app = Application(modules=[HelloModule()])

# Equivalente, encadenable (Opción B, no usada aquí para no duplicar el ejemplo):
#   app = Application().add_module(HelloModule())

if __name__ == "__main__":
    print(f"TEAF {app.version}")

    # Entrar en el lifespan arranca el Runtime Y bootstrapea "hello" —
    # ningún código de este archivo llama a module.bootstrap() a mano.
    with TestClient(app.asgi):
        print(f"Módulos registrados: {[m.name for m in app.runtime.modules]}")
        has_capability = app.runtime.capability_registry.exists("hello.greet")
        print(f"Capacidad 'hello.greet' registrada: {has_capability}")
