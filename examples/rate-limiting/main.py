"""Rate limiting — los cuatro algoritmos y las dimensiones de agrupación.

Compara ``FIXED_WINDOW``/``SLIDING_WINDOW``/``TOKEN_BUCKET``/``LEAKY_BUCKET``
sobre la misma secuencia de peticiones, y después monta el limitador sobre
una aplicación real para ver las cabeceras ``X-RateLimit-*`` y el rechazo
429 con ``Retry-After``.

Ejecutar:

    python examples/rate-limiting/main.py
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf.api import (
    ApiGateway,
    ApiRequestContext,
    ProtectionScope,
    RateLimitAlgorithm,
    RateLimiter,
    RateLimitRule,
)


async def compare_algorithms() -> None:
    """Ocho peticiones seguidas contra un límite de 3 por cada algoritmo."""
    print("== Los cuatro algoritmos, mismo límite (3 peticiones / 10 s) ==")
    for algorithm in RateLimitAlgorithm:
        limiter = RateLimiter(
            [
                RateLimitRule(
                    name="demo",
                    limit=3,
                    window_seconds=10.0,
                    algorithm=algorithm,
                    scope=ProtectionScope.IP,
                )
            ]
        )
        context = ApiRequestContext(client_ip="10.0.0.1")
        marks = []
        for _ in range(8):
            denial = await limiter.acquire(context)
            marks.append("." if denial is None else "x")
        print(f"  {algorithm.value:<15} {''.join(marks)}   (. aceptada, x rechazada)")


async def compare_scopes() -> None:
    """La misma regla agrupa distinto según la dimensión elegida."""
    print("\n== Dimensiones: cada tenant tiene su propio presupuesto ==")
    limiter = RateLimiter(
        [RateLimitRule(name="por-tenant", limit=2, window_seconds=60, scope=ProtectionScope.TENANT)]
    )
    for tenant in ("acme", "acme", "acme", "globex"):
        denial = await limiter.acquire(ApiRequestContext(tenant_id=tenant))
        estado = "rechazada" if denial else "aceptada"
        print(f"  tenant={tenant:<8} {estado}")


def over_http() -> None:
    """El mismo limitador, ya montado sobre una aplicación."""
    print("\n== Sobre HTTP: cabeceras y rechazo 429 ==")
    app = FastAPI()

    @app.get("/items")
    def items() -> dict[str, str]:
        return {"status": "ok"}

    ApiGateway(
        rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=2, window_seconds=60)])
    ).install(app)

    client = TestClient(app)
    for intento in range(1, 4):
        response = client.get("/items")
        restantes = response.headers.get("X-RateLimit-Remaining", "-")
        reintentar = response.headers.get("Retry-After", "-")
        print(
            f"  petición {intento}: HTTP {response.status_code} | "
            f"X-RateLimit-Remaining={restantes} | Retry-After={reintentar}"
        )
    print(f"  cuerpo del rechazo: {response.json()['detail']}")


async def main() -> None:
    await compare_algorithms()
    await compare_scopes()
    over_http()


if __name__ == "__main__":
    asyncio.run(main())
