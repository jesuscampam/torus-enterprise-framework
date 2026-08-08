"""Quota management — consumo contratado por período, ancho de banda y concurrencia.

Las cuotas gobiernan *cuánto le corresponde* a un cliente (al mes, al día),
a diferencia del rate limiting, que protege la *disponibilidad* del servicio
en ventanas de segundos. Este ejemplo muestra las cuatro magnitudes de
``QuotaKind``.

Ejecutar:

    python examples/quota-management/main.py
"""

from __future__ import annotations

import asyncio

from teaf.api import (
    ApiRequestContext,
    ProtectionScope,
    QuotaKind,
    QuotaManager,
    QuotaPeriod,
    QuotaRule,
)


async def requests_per_period() -> None:
    print("== Cuota de peticiones por día (3 por tenant) ==")
    manager = QuotaManager(
        [
            QuotaRule(
                name="diaria",
                kind=QuotaKind.REQUESTS,
                limit=3,
                period=QuotaPeriod.DAY,
                scope=ProtectionScope.TENANT,
            )
        ]
    )
    context = ApiRequestContext(tenant_id="acme")
    for intento in range(1, 5):
        denial = await manager.consume(context)
        if denial is None:
            (usage,) = await manager.usage(context)
            print(f"  petición {intento}: aceptada  (consumido {usage.consumed:.0f}/{usage.limit})")
        else:
            print(
                f"  petición {intento}: RECHAZADA (cuota '{denial.usage.rule}' agotada, "
                f"reintentar en {denial.retry_after_seconds / 3600:.1f} h)"
            )


async def bandwidth_and_payload() -> None:
    print("\n== Ancho de banda acumulado vs. tamaño de una sola petición ==")
    manager = QuotaManager(
        [
            QuotaRule(
                name="ancho-banda",
                kind=QuotaKind.BANDWIDTH,
                limit=5_000,
                period=QuotaPeriod.DAY,
                scope=ProtectionScope.TENANT,
            ),
            QuotaRule(
                name="payload", kind=QuotaKind.PAYLOAD, limit=600, scope=ProtectionScope.TENANT
            ),
        ]
    )
    for tamano in (400, 400, 400, 900):
        context = ApiRequestContext(tenant_id="acme", request_bytes=tamano)
        denial = await manager.consume(context)
        motivo = "aceptada" if denial is None else f"RECHAZADA por '{denial.usage.rule}'"
        print(f"  petición de {tamano:>4} bytes: {motivo}")


async def concurrency() -> None:
    print("\n== Cuota de concurrencia: sube al entrar, baja al salir ==")
    manager = QuotaManager(
        [
            QuotaRule(
                name="simultaneas", kind=QuotaKind.CONCURRENT, limit=2, scope=ProtectionScope.TENANT
            )
        ]
    )
    context = ApiRequestContext(tenant_id="acme")

    async def entra(etiqueta: str) -> None:
        aceptada = await manager.consume(context) is None
        print(f"  entra petición {etiqueta}: {'aceptada' if aceptada else 'RECHAZADA'}")

    await entra("A")
    await entra("B")
    await entra("C")
    await manager.release(context)
    print("  termina la petición A (release)")
    await entra("D")


async def main() -> None:
    await requests_per_period()
    await bandwidth_and_payload()
    await concurrency()


if __name__ == "__main__":
    asyncio.run(main())
