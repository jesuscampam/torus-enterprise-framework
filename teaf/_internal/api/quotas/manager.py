"""``QuotaManager`` — cuotas de consumo por período y dimensión (Sprint 2.9, ADR-009).

Diferencia con rate limiting, que es la pregunta que más se repite: el rate
limiting protege la *disponibilidad* del servicio (¿cuántas peticiones por
segundo aguanta esto?) y opera en ventanas de segundos; las cuotas gobiernan
el *consumo contratado* de un cliente (¿cuánto le corresponde este mes?) y
operan en ventanas de minutos a meses. De ahí que sean dos subsistemas y no
uno: comparten las dimensiones (``ProtectionScope``) pero no el propósito,
ni el orden de magnitud, ni el algoritmo.

Las cuatro magnitudes de ``QuotaKind`` se evalúan de forma distinta:

- ``REQUESTS`` y ``BANDWIDTH`` **acumulan** sobre la ventana del período.
- ``PAYLOAD`` es un límite *por petición* — no acumula, solo compara.
- ``CONCURRENT`` cuenta peticiones simultáneas: sube al entrar y baja al
  salir (``release()``), sin ventana temporal.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from teaf._internal.api.models import (
    ApiRequestContext,
    QuotaDecision,
    QuotaKind,
    QuotaRule,
    QuotaUsage,
    period_seconds,
    resolve_scope_key,
)
from teaf._internal.api.providers.memory import Clock, InMemoryQuotaStore
from teaf._internal.contracts.api import QuotaStore


def build_quota_key(rule: QuotaRule, context: ApiRequestContext, *, now: float) -> str:
    """Clave de almacén de ``rule`` para ``context`` en la ventana que contiene ``now``.

    Para las cuotas acumulativas la clave incorpora el índice de ventana
    (``now // duración``), de modo que al cambiar de período la clave cambia
    y el consumo arranca de cero sin necesitar ningún proceso de reinicio.
    Las cuotas de concurrencia no llevan índice: no tienen ventana.
    """
    dimension = f"{rule.name}:{rule.scope.value}:{resolve_scope_key(rule.scope, context)}"
    if not rule.accumulates:
        return dimension
    window_index = int(now // period_seconds(rule.period))
    return f"{dimension}:{window_index}"


class QuotaManager:
    """Aplica un conjunto de ``QuotaRule`` sobre las peticiones entrantes."""

    def __init__(
        self,
        rules: Sequence[QuotaRule] = (),
        *,
        store: QuotaStore | None = None,
        clock: Clock = time.time,
        enabled: bool = True,
    ) -> None:
        self._rules = tuple(rules)
        self._store = store if store is not None else InMemoryQuotaStore(clock=clock)
        self._clock = clock
        self._enabled = enabled

    @property
    def rules(self) -> tuple[QuotaRule, ...]:
        """Cuotas configuradas, en orden de evaluación."""
        return self._rules

    @property
    def enabled(self) -> bool:
        """``False`` desactiva las cuotas sin desmontar el middleware."""
        return self._enabled

    @property
    def store(self) -> QuotaStore:
        """Almacén sobre el que se persiste el consumo."""
        return self._store

    async def consume(self, context: ApiRequestContext) -> QuotaDecision | None:
        """Consume todas las cuotas aplicables a ``context``.

        Devuelve la decisión de la primera cuota agotada, o ``None`` si todas
        admiten la petición. ``request_bytes`` de ``context`` es lo que
        alimenta las cuotas de ``BANDWIDTH`` y ``PAYLOAD``.
        """
        if not self._enabled:
            return None

        for rule in self._rules:
            decision = await self._consume_rule(rule, context)
            if not decision.allowed:
                return decision
        return None

    async def release(self, context: ApiRequestContext) -> None:
        """Libera las cuotas de concurrencia tomadas por ``consume()``.

        Debe llamarse siempre que ``consume()`` haya aceptado la petición —
        incluso si el endpoint falló—, o el contador de concurrencia se
        quedaría alto para siempre. ``QuotaMiddleware`` lo garantiza con un
        ``finally``.
        """
        if not self._enabled:
            return
        now = self._clock()
        for rule in self._rules:
            if rule.kind is QuotaKind.CONCURRENT:
                await self._store.release(build_quota_key(rule, context, now=now), 1.0)

    async def usage(self, context: ApiRequestContext) -> tuple[QuotaUsage, ...]:
        """Consumo actual de cada cuota aplicable a ``context``, sin consumir nada."""
        now = self._clock()
        usages: list[QuotaUsage] = []
        for rule in self._rules:
            key = build_quota_key(rule, context, now=now)
            consumed = 0.0 if rule.kind is QuotaKind.PAYLOAD else await self._store.peek(key)
            usages.append(
                QuotaUsage(
                    rule=rule.name,
                    kind=rule.kind,
                    key=key,
                    consumed=consumed,
                    limit=rule.limit,
                    period=rule.period,
                )
            )
        return tuple(usages)

    async def reset(self, context: ApiRequestContext) -> None:
        """Elimina el consumo acumulado de todas las cuotas aplicables a ``context``."""
        now = self._clock()
        for rule in self._rules:
            await self._store.reset(build_quota_key(rule, context, now=now))

    def _amount_for(self, rule: QuotaRule, context: ApiRequestContext) -> float:
        """Cuánto consume ``context`` de ``rule`` — depende de la magnitud medida."""
        if rule.kind in (QuotaKind.BANDWIDTH, QuotaKind.PAYLOAD):
            return float(context.request_bytes)
        return 1.0

    async def _consume_rule(self, rule: QuotaRule, context: ApiRequestContext) -> QuotaDecision:
        now = self._clock()
        key = build_quota_key(rule, context, now=now)
        amount = self._amount_for(rule, context)

        if rule.kind is QuotaKind.PAYLOAD:
            # Límite por petición: no acumula, así que no toca el almacén.
            usage = QuotaUsage(
                rule=rule.name,
                kind=rule.kind,
                key=key,
                consumed=amount,
                limit=rule.limit,
                period=rule.period,
            )
            return QuotaDecision(allowed=amount <= rule.limit, usage=usage)

        window = period_seconds(rule.period)
        total = await self._store.consume(key, amount, ttl_seconds=window)
        allowed = total <= rule.limit
        if not allowed:
            # Deshacer el consumo que acaba de desbordar la cuota: si no, una
            # petición rechazada seguiría contando y el cliente nunca vería
            # bajar el contador aunque dejara de insistir.
            total = await self._store.release(key, amount)

        usage = QuotaUsage(
            rule=rule.name,
            kind=rule.kind,
            key=key,
            consumed=total,
            limit=rule.limit,
            period=rule.period,
        )
        retry_after = 0.0
        if not allowed and rule.accumulates:
            retry_after = window - (now % window)
        return QuotaDecision(allowed=allowed, usage=usage, retry_after_seconds=retry_after)
