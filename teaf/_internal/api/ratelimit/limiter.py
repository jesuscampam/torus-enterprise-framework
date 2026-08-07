"""``RateLimiter`` — evalúa una petición contra todas las reglas aplicables (Sprint 2.9).

Combina las tres piezas que hasta ahora eran independientes: las reglas
(``RateLimitRule``, ``models.py``), los algoritmos puros
(``algorithms.py``) y el almacén (``RateLimitStore``, ``contracts/api.py``).

Semántica de varias reglas: **todas** las reglas aplicables se evalúan y la
petición se acepta solo si todas la aceptan. Cuando alguna rechaza, se
devuelve la decisión de la *primera* que lo hizo, y ninguna de las reglas
posteriores llega a consumir cuota — así un rechazo por una regla laxa no
gasta el presupuesto de las demás. Las ya evaluadas antes del rechazo sí
consumieron: es el precio de no poder deshacer una escritura distribuida, y
la alternativa (evaluar en seco y luego confirmar) duplicaría el coste de
cada petición sin eliminar del todo la ventana de carrera.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from teaf._internal.api.models import (
    ApiRequestContext,
    RateLimitAlgorithm,
    RateLimitDecision,
    RateLimitRule,
    resolve_scope_key,
)
from teaf._internal.api.providers.memory import Clock, InMemoryRateLimitStore
from teaf._internal.api.ratelimit.algorithms import get_algorithm
from teaf._internal.contracts.api import RateLimitStore


def build_rate_limit_key(rule: RateLimitRule, context: ApiRequestContext) -> str:
    """Clave de almacén de ``rule`` para ``context``: ``"<regla>:<dimensión>:<valor>"``.

    Incluir el nombre de la regla es lo que permite que dos reglas con la
    misma dimensión (p. ej. "100/minuto por IP" y "5000/día por IP")
    convivan sobre el mismo almacén sin pisarse.
    """
    return f"{rule.name}:{rule.scope.value}:{resolve_scope_key(rule.scope, context)}"


class RateLimiter:
    """Aplica un conjunto de ``RateLimitRule`` sobre las peticiones entrantes.

    Sin reglas configuradas no limita nada y ``acquire()`` acepta siempre:
    activar la plataforma de protección nunca puede romper una aplicación
    que aún no ha declarado sus límites (ver docs/api/RATE-LIMITING.md).
    """

    def __init__(
        self,
        rules: Sequence[RateLimitRule] = (),
        *,
        store: RateLimitStore | None = None,
        clock: Clock = time.time,
        enabled: bool = True,
    ) -> None:
        self._rules = tuple(rules)
        self._store = store if store is not None else InMemoryRateLimitStore(clock=clock)
        self._clock = clock
        self._enabled = enabled

    @property
    def rules(self) -> tuple[RateLimitRule, ...]:
        """Reglas configuradas, en orden de evaluación."""
        return self._rules

    @property
    def enabled(self) -> bool:
        """``False`` desactiva la limitación por completo sin desmontar el middleware."""
        return self._enabled

    @property
    def store(self) -> RateLimitStore:
        """Almacén sobre el que se persiste el estado de las reglas."""
        return self._store

    def rules_for(self, context: ApiRequestContext) -> tuple[RateLimitRule, ...]:
        """Reglas que aplican a ``context`` (filtradas por endpoint y rol)."""
        return tuple(rule for rule in self._rules if rule.matches(context))

    async def acquire(
        self, context: ApiRequestContext, *, cost: float = 1.0
    ) -> RateLimitDecision | None:
        """Consume cuota para ``context``; devuelve la decisión de rechazo, o ``None`` si pasa.

        Devolver ``None`` cuando se acepta (en vez de una decisión con
        ``allowed=True``) mantiene el caso normal sin coste de interpretación
        para el llamante; ``inspect()`` es la vía para ver el detalle de
        todas las reglas sin consumir nada.
        """
        if not self._enabled:
            return None

        for rule in self.rules_for(context):
            decision = await self._evaluate(rule, context, cost=cost, persist=True)
            if not decision.allowed:
                return decision
        return None

    async def inspect(self, context: ApiRequestContext) -> tuple[RateLimitDecision, ...]:
        """Estado actual de cada regla aplicable, **sin consumir cuota**.

        Es lo que alimenta las cabeceras ``X-RateLimit-*`` informativas y los
        paneles de diagnóstico: evalúa con coste 0 y nunca escribe en el
        almacén.
        """
        decisions: list[RateLimitDecision] = []
        for rule in self.rules_for(context):
            decisions.append(await self._evaluate(rule, context, cost=0.0, persist=False))
        return tuple(decisions)

    async def reset(self, context: ApiRequestContext) -> None:
        """Elimina el estado de todas las reglas aplicables a ``context``."""
        for rule in self.rules_for(context):
            await self._store.reset(build_rate_limit_key(rule, context))

    async def _evaluate(
        self, rule: RateLimitRule, context: ApiRequestContext, *, cost: float, persist: bool
    ) -> RateLimitDecision:
        key = build_rate_limit_key(rule, context)
        algorithm = get_algorithm(rule.algorithm)
        state = await self._store.get(key)
        new_state, decision = algorithm.evaluate(
            state, rule=rule, key=key, now=self._clock(), cost=cost
        )
        # Ventana fija es el único algoritmo cuyo contador avanza también con
        # las peticiones rechazadas (ver algorithms.py) — persistir su estado
        # aun cuando se rechaza es lo que hace real ese comportamiento. En
        # los otros tres, un rechazo no deja rastro, así que no hay nada que
        # guardar.
        counts_rejections = rule.algorithm is RateLimitAlgorithm.FIXED_WINDOW
        if persist and (decision.allowed or counts_rejections):
            await self._store.put(key, new_state, ttl_seconds=algorithm.ttl_seconds(rule))
        return decision
