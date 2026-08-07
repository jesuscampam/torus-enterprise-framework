"""Los cuatro algoritmos de rate limiting (Sprint 2.9, ADR-009).

Cada algoritmo es una **función pura sobre el estado**: recibe el
``RateLimitState`` anterior (o ``None``) y devuelve el estado nuevo más la
``RateLimitDecision``. No hacen I/O, no conocen el almacén y no leen el
reloj por su cuenta — ``now`` llega como argumento. Esa separación es lo
que permite probar los cuatro exhaustivamente, incluido el comportamiento
en los bordes de ventana, sin dormir ni levantar Redis; ``RateLimiter``
(``limiter.py``) es quien los combina con un ``RateLimitStore``.

Diferencia deliberada entre algoritmos, documentada porque sorprende: en
**ventana fija** una petición rechazada *sí* consume cuota (es un
"incrementa y compara", el patrón clásico ``INCR`` de Redis), mientras que
en los otros tres una petición rechazada **no** deja rastro. Es el
comportamiento estándar de cada uno: un cubo del que no se pudo sacar un
token no pierde tokens, y un registro deslizante que anotase los rechazos
impediría al cliente recuperarse hasta que pasara la ventana completa.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from teaf._internal.api.models import (
    RateLimitAlgorithm,
    RateLimitDecision,
    RateLimitRule,
    RateLimitState,
)


class RateLimitAlgorithmBase(ABC):
    """Contrato de un algoritmo de limitación: estado anterior → estado nuevo + decisión."""

    @abstractmethod
    def evaluate(
        self,
        state: RateLimitState | None,
        *,
        rule: RateLimitRule,
        key: str,
        now: float,
        cost: float,
    ) -> tuple[RateLimitState, RateLimitDecision]:
        """Evalúa una petición de coste ``cost`` contra ``rule`` en el instante ``now``."""
        ...

    def ttl_seconds(self, rule: RateLimitRule) -> float:
        """Cuánto debe sobrevivir el estado en el almacén.

        El doble de la ventana por defecto: suficiente para que el estado no
        expire mientras siga siendo relevante, y lo bastante corto para que
        una clave que deja de recibir tráfico se libere sola.
        """
        return max(rule.window_seconds, 1.0) * 2


class FixedWindowAlgorithm(RateLimitAlgorithmBase):
    """Ventana fija: un contador por bloque de tiempo alineado al reloj.

    El más barato de todos (un entero por clave) y el más fácil de razonar,
    a cambio de su limitación conocida: un cliente puede emitir ``limit``
    peticiones al final de una ventana y otras ``limit`` al principio de la
    siguiente — hasta el doble del límite nominal en un instante. Cuando eso
    importa, la alternativa directa es ``SlidingWindowAlgorithm``.
    """

    def evaluate(
        self,
        state: RateLimitState | None,
        *,
        rule: RateLimitRule,
        key: str,
        now: float,
        cost: float,
    ) -> tuple[RateLimitState, RateLimitDecision]:
        window = max(rule.window_seconds, 1e-9)
        window_start = (now // window) * window
        previous = state.count if state is not None and state.window_start == window_start else 0

        count = previous + int(cost)
        allowed = count <= rule.limit
        reset_after = window_start + window - now

        new_state = RateLimitState(count=count, window_start=window_start, updated_at=now)
        decision = RateLimitDecision(
            allowed=allowed,
            rule=rule.name,
            key=key,
            limit=rule.limit,
            remaining=max(0, rule.limit - count),
            reset_after_seconds=reset_after,
            retry_after_seconds=0.0 if allowed else reset_after,
        )
        return new_state, decision


class SlidingWindowAlgorithm(RateLimitAlgorithmBase):
    """Ventana deslizante por registro: guarda la marca de tiempo de cada petición aceptada.

    Exacto —nunca permite más de ``limit`` peticiones en *ningún* intervalo
    de ``window_seconds``, no solo en los bloques alineados— a cambio de
    guardar hasta ``limit`` marcas de tiempo por clave. Como solo se anotan
    las peticiones aceptadas, el registro no puede crecer por encima de
    ``limit`` por muchos rechazos que haya.
    """

    def evaluate(
        self,
        state: RateLimitState | None,
        *,
        rule: RateLimitRule,
        key: str,
        now: float,
        cost: float,
    ) -> tuple[RateLimitState, RateLimitDecision]:
        window = max(rule.window_seconds, 1e-9)
        cutoff = now - window
        kept = tuple(t for t in (state.timestamps if state is not None else ()) if t > cutoff)

        units = max(1, int(cost))
        allowed = len(kept) + units <= rule.limit
        timestamps = kept + (now,) * units if allowed else kept

        # Cuando se rechaza, el cliente vuelve a tener hueco en cuanto salgan
        # de la ventana las ``excess`` marcas más antiguas — no cuando salgan
        # todas, que sería innecesariamente pesimista.
        oldest = timestamps[0] if timestamps else now
        reset_after = max(0.0, oldest + window - now)
        retry_after = 0.0
        if not allowed and kept:
            excess = len(kept) + units - rule.limit
            index = min(max(excess - 1, 0), len(kept) - 1)
            retry_after = max(0.0, kept[index] + window - now)

        new_state = RateLimitState(timestamps=timestamps, updated_at=now)
        decision = RateLimitDecision(
            allowed=allowed,
            rule=rule.name,
            key=key,
            limit=rule.limit,
            remaining=max(0, rule.limit - len(timestamps)),
            reset_after_seconds=reset_after,
            retry_after_seconds=retry_after,
        )
        return new_state, decision


class TokenBucketAlgorithm(RateLimitAlgorithmBase):
    """Cubo de tokens: se rellena a ritmo constante y admite ráfagas hasta ``rule.capacity``.

    El algoritmo de referencia cuando se quiere permitir picos cortos sin
    renunciar a un caudal medio: ``rule.burst`` fija cuánta ráfaga se tolera
    y ``rule.limit``/``rule.window_seconds`` el caudal sostenido. Un cubo
    nuevo arranca lleno, para no penalizar a un cliente por ser el primero.
    """

    def evaluate(
        self,
        state: RateLimitState | None,
        *,
        rule: RateLimitRule,
        key: str,
        now: float,
        cost: float,
    ) -> tuple[RateLimitState, RateLimitDecision]:
        capacity = float(rule.capacity)
        rate = max(rule.refill_rate, 1e-9)

        if state is None:
            tokens = capacity
        else:
            elapsed = max(0.0, now - state.updated_at)
            tokens = min(capacity, state.tokens + elapsed * rate)

        allowed = tokens >= cost
        if allowed:
            tokens -= cost

        new_state = RateLimitState(tokens=tokens, updated_at=now)
        decision = RateLimitDecision(
            allowed=allowed,
            rule=rule.name,
            key=key,
            limit=rule.capacity,
            remaining=int(tokens),
            reset_after_seconds=(capacity - tokens) / rate,
            retry_after_seconds=0.0 if allowed else (cost - tokens) / rate,
        )
        return new_state, decision

    def ttl_seconds(self, rule: RateLimitRule) -> float:
        """El doble de lo que tarda el cubo en volver a llenarse desde vacío."""
        return max(rule.capacity / max(rule.refill_rate, 1e-9), 1.0) * 2


class LeakyBucketAlgorithm(RateLimitAlgorithmBase):
    """Cubo con fuga: la cola se drena a ritmo constante y se rechaza al desbordar.

    Complementario del cubo de tokens: en vez de acumular permisos mientras
    hay silencio, acumula *trabajo pendiente* y lo drena a caudal fijo. Es
    el adecuado cuando lo que se protege es un recurso aguas abajo que no
    tolera ráfagas (una cola de mensajes, un sistema legado), porque suaviza
    el tráfico en lugar de dejarlo pasar a picos.
    """

    def evaluate(
        self,
        state: RateLimitState | None,
        *,
        rule: RateLimitRule,
        key: str,
        now: float,
        cost: float,
    ) -> tuple[RateLimitState, RateLimitDecision]:
        capacity = float(rule.capacity)
        leak_rate = max(rule.refill_rate, 1e-9)

        if state is None:
            level = 0.0
        else:
            elapsed = max(0.0, now - state.updated_at)
            level = max(0.0, state.tokens - elapsed * leak_rate)

        allowed = level + cost <= capacity
        overflow = level + cost - capacity
        if allowed:
            level += cost

        new_state = RateLimitState(tokens=level, updated_at=now)
        decision = RateLimitDecision(
            allowed=allowed,
            rule=rule.name,
            key=key,
            limit=rule.capacity,
            remaining=int(max(0.0, capacity - level)),
            reset_after_seconds=level / leak_rate,
            retry_after_seconds=0.0 if allowed else overflow / leak_rate,
        )
        return new_state, decision

    def ttl_seconds(self, rule: RateLimitRule) -> float:
        """El doble de lo que tarda el cubo en drenarse desde lleno."""
        return max(rule.capacity / max(rule.refill_rate, 1e-9), 1.0) * 2


#: Instancia única por algoritmo — no tienen estado propio (todo el estado
#: viaja en ``RateLimitState``), así que compartirlas es seguro y evita
#: construir un objeto por petición.
_ALGORITHMS: dict[RateLimitAlgorithm, RateLimitAlgorithmBase] = {
    RateLimitAlgorithm.FIXED_WINDOW: FixedWindowAlgorithm(),
    RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowAlgorithm(),
    RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketAlgorithm(),
    RateLimitAlgorithm.LEAKY_BUCKET: LeakyBucketAlgorithm(),
}


def get_algorithm(algorithm: RateLimitAlgorithm) -> RateLimitAlgorithmBase:
    """Devuelve la implementación de ``algorithm``."""
    return _ALGORITHMS[algorithm]
