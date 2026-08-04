"""``Pipeline`` — secuencia ordenada de pasos de inicialización o apagado.

Cada módulo futuro podrá añadir su propio paso con ``add_step(name, action)``.
``StartupPipeline`` ejecuta los pasos en el orden en que se registraron;
``ShutdownPipeline`` los ejecuta en orden inverso (LIFO — el último recurso
adquirido es el primero en liberarse), consistente con la práctica habitual
de limpieza de recursos.
"""

from __future__ import annotations

from dataclasses import dataclass

from teaf._internal.runtime.exceptions import LifecycleException
from teaf._internal.runtime.hooks import Hook, invoke_hook


@dataclass(frozen=True, slots=True)
class PipelineStep:
    """Un paso nombrado de un ``Pipeline`` — el nombre existe para poder loguear/depurar."""

    name: str
    action: Hook


class Pipeline:
    """Secuencia ordenada de pasos ejecutados uno tras otro."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._steps: list[PipelineStep] = []

    def add_step(self, name: str, action: Hook) -> None:
        """Añade un paso llamado ``name`` al final de la secuencia."""
        self._steps.append(PipelineStep(name=name, action=action))

    def steps(self) -> tuple[PipelineStep, ...]:
        """Pasos en el orden en que ``run()`` los ejecutará."""
        return tuple(self._steps)

    async def run(self) -> None:
        """Ejecuta cada paso en el orden de ``steps()``.

        Raises:
            LifecycleException: si algún paso falla — envuelve la excepción
                original indicando el pipeline y el paso que falló.
        """
        for step in self.steps():
            try:
                await invoke_hook(step.action)
            except Exception as exc:
                raise LifecycleException(
                    f"El paso '{step.name}' del pipeline '{self.name}' falló: {exc}"
                ) from exc


class StartupPipeline(Pipeline):
    """Pipeline de inicialización: ejecuta los pasos en orden de registro (FIFO)."""

    def __init__(self) -> None:
        super().__init__(name="startup")


class ShutdownPipeline(Pipeline):
    """Pipeline de apagado: ejecuta los pasos en orden inverso al de registro (LIFO)."""

    def __init__(self) -> None:
        super().__init__(name="shutdown")

    def steps(self) -> tuple[PipelineStep, ...]:
        return tuple(reversed(self._steps))
