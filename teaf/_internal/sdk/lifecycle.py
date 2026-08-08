"""``ModuleLifecycle`` — estado de ciclo de vida de una instancia de módulo.

Vocabulario propio del SDK — deliberadamente distinto de
``LifecycleStage`` (``backend.runtime.lifecycle``, las etapas del
*Runtime*) y de ``ModuleLifecycleState`` de ``backend.core.registry`` (el
estado de un módulo *ya registrado*, un vocabulario más simple pensado solo
para el catálogo). Este describe las ocho etapas por las que pasa una
instancia concreta de ``ModuleBase`` durante ``bootstrap()``/``shutdown()``
(ver ``module_base.py``).
"""

from __future__ import annotations

from enum import Enum


class ModuleLifecycleState(str, Enum):
    """Etapas del ciclo de vida de un módulo, en el orden canónico en que ocurren."""

    CREATED = "created"
    INITIALIZED = "initialized"
    CONFIGURED = "configured"
    REGISTERED = "registered"
    STARTED = "started"
    READY = "ready"
    STOPPED = "stopped"
    DISPOSED = "disposed"
    FAILED = "failed"


#: Orden canónico de las etapas "felices" (sin contar ``FAILED``, que puede
#: alcanzarse desde cualquier punto). Usado por ``ModuleLifecycle.advance()``
#: para detectar retrocesos y por ``ModuleValidator`` para documentación.
CANONICAL_ORDER: tuple[ModuleLifecycleState, ...] = (
    ModuleLifecycleState.CREATED,
    ModuleLifecycleState.INITIALIZED,
    ModuleLifecycleState.CONFIGURED,
    ModuleLifecycleState.REGISTERED,
    ModuleLifecycleState.STARTED,
    ModuleLifecycleState.READY,
    ModuleLifecycleState.STOPPED,
    ModuleLifecycleState.DISPOSED,
)


class ModuleLifecycle:
    """Rastrea el estado actual y el historial de transiciones de un módulo."""

    def __init__(self) -> None:
        self._state = ModuleLifecycleState.CREATED
        self._history: list[ModuleLifecycleState] = [self._state]

    @property
    def state(self) -> ModuleLifecycleState:
        """Etapa actual."""
        return self._state

    @property
    def history(self) -> tuple[ModuleLifecycleState, ...]:
        """Todas las etapas alcanzadas, en el orden en que ocurrieron."""
        return tuple(self._history)

    def advance(self, state: ModuleLifecycleState) -> None:
        """Registra la transición a ``state``.

        ``FAILED`` es válido desde cualquier etapa. Cualquier otra
        transición hacia atrás en ``CANONICAL_ORDER`` respecto a la etapa
        actual se rechaza — un módulo no puede "volver a inicializarse"
        sin pasar por un ``ModuleLifecycle`` nuevo.

        Raises:
            ValueError: si ``state`` no es un avance válido desde la etapa actual.
        """
        if state is not ModuleLifecycleState.FAILED:
            if self._state is ModuleLifecycleState.FAILED:
                raise ValueError("El módulo falló: no puede continuar su ciclo de vida.")
            if state in CANONICAL_ORDER and self._state in CANONICAL_ORDER:
                if CANONICAL_ORDER.index(state) <= CANONICAL_ORDER.index(self._state):
                    raise ValueError(
                        f"Transición inválida: '{self._state.value}' -> '{state.value}' "
                        "retrocede en el ciclo de vida."
                    )
        self._state = state
        self._history.append(state)

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) del estado actual y su historial."""
        return {
            "state": self._state.value,
            "history": [s.value for s in self._history],
        }
