"""``LifecycleManager`` — etapas del ciclo de vida del Framework.

Cuatro etapas (``LifecycleStage``): Bootstrap → Startup → Running →
Shutdown. Cualquier pieza del Runtime (o, en el futuro, un módulo o
plugin) puede registrar un hook para una etapa; ``Runtime`` (ver
``runtime.py``) es responsable de avanzar las etapas en orden durante el
arranque y el apagado.
"""

from __future__ import annotations

from enum import Enum

from teaf._internal.runtime.exceptions import LifecycleException
from teaf._internal.runtime.hooks import Hook, invoke_hook


class LifecycleStage(str, Enum):
    """Etapas del ciclo de vida del Runtime, en el orden en que se ejecutan."""

    BOOTSTRAP = "bootstrap"
    STARTUP = "startup"
    RUNNING = "running"
    SHUTDOWN = "shutdown"
    STOPPED = "stopped"


class LifecycleManager:
    """Registra hooks por etapa y los ejecuta cuando el Runtime avanza de etapa."""

    def __init__(self) -> None:
        self._hooks: dict[LifecycleStage, list[Hook]] = {stage: [] for stage in LifecycleStage}
        self._current_stage: LifecycleStage | None = None

    @property
    def current_stage(self) -> LifecycleStage | None:
        """Última etapa completada, o ``None`` si el Runtime todavía no arrancó."""
        return self._current_stage

    def on(self, stage: LifecycleStage, hook: Hook) -> None:
        """Registra ``hook`` para ejecutarse cuando el Runtime alcance ``stage``."""
        self._hooks[stage].append(hook)

    async def run_stage(self, stage: LifecycleStage) -> None:
        """Ejecuta, en orden de registro, todos los hooks de ``stage``.

        Raises:
            LifecycleException: si algún hook lanza una excepción — se
                envuelve para dejar claro en qué etapa y hook falló.
        """
        for index, hook in enumerate(self._hooks[stage]):
            try:
                await invoke_hook(hook)
            except Exception as exc:
                raise LifecycleException(
                    f"El hook #{index} de la etapa '{stage.value}' falló: {exc}"
                ) from exc
        self._current_stage = stage
