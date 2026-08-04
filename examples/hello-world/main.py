"""Hello World — el ejemplo mínimo de una aplicación TEAF.

Construye una ``Application``, arranca su ``Runtime`` y lo apaga de nuevo.
Ninguna dependencia salvo ``teaf`` — ni una sola línea conoce ``teaf/_internal/``.

Ejecutar:

    python examples/hello-world/main.py
"""

from __future__ import annotations

import asyncio

from teaf import Application


async def main() -> None:
    app = Application()
    print(f"TEAF {app.version}")

    await app.runtime.startup()
    print(f"Runtime state: {app.runtime.state.value}")

    await app.runtime.shutdown()
    print(f"Runtime state: {app.runtime.state.value}")


if __name__ == "__main__":
    asyncio.run(main())
