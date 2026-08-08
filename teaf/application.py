"""``teaf.application`` — construir una aplicación TEAF.

``Application`` envuelve ``create_app()`` (``teaf/_internal/core/application.py``,
Sprint 2.1/2.3): el *composition root* interno que ensambla configuración,
logging, middlewares, rutas de sistema y el ``Runtime``. Ningún consumidor
público necesita conocer ``create_app`` ni ``teaf._internal.core.application`` —
``Application`` es la única puerta de entrada.

Es también un callable ASGI (implementa ``__call__(scope, receive, send)``),
así que una instancia se sirve directamente con cualquier servidor ASGI:

    # app.py
    from teaf import Application
    app = Application()

    # uvicorn app:app

Desde Sprint 2.6.3 (Module Registration API), ``Application`` también
registra módulos usando exclusivamente la API pública — sin conocer el
``Runtime``, sin llamar a ``bootstrap()`` a mano, sin ``asyncio.run()``:

    from teaf import Application

    app = Application(modules=[TaskModule(), CustomerModule()])

    # equivalente, encadenable:
    app = Application().add_module(TaskModule()).add_module(CustomerModule())

Los módulos pasados así arrancan automáticamente cuando arranca el ciclo de
vida ASGI de la aplicación (servida con ``uvicorn`` o entrando en su
lifespan, p. ej. con ``TestClient``) — el ciclo de vida lo sigue
controlando TEAF, nunca el consumidor.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from starlette.types import Receive, Scope, Send

from teaf._internal.config.settings import Settings
from teaf._internal.core.application import FRAMEWORK_VERSION, create_app
from teaf._internal.runtime.runtime import Runtime
from teaf._internal.sdk.module_base import ModuleBase


class Application:
    """Fachada pública de una aplicación TEAF en ejecución."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        modules: Sequence[ModuleBase] | None = None,
    ) -> None:
        """Construye la aplicación. ``settings=None`` resuelve la configuración del
        entorno. ``modules`` (Sprint 2.6.3) se arrancan automáticamente contra el
        ``Runtime`` cuando arranque el ciclo de vida ASGI — ver docstring del módulo."""
        self._asgi_app: FastAPI = create_app(settings, modules=modules)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Interfaz ASGI — permite servir una instancia directamente (``uvicorn app:app``)."""
        await self._asgi_app(scope, receive, send)

    def add_module(self, module: ModuleBase) -> Application:
        """Añade ``module`` a los módulos pendientes de arranque (Sprint 2.6.3).

        Encadenable: ``Application().add_module(A()).add_module(B())``. Debe
        llamarse antes de que arranque el ciclo de vida de la aplicación
        (antes de servirla o de entrar en su lifespan) — un módulo añadido
        después de ese punto no arranca retroactivamente.
        """
        self._asgi_app.state.pending_modules.append(module)
        return self

    @property
    def runtime(self) -> Runtime:
        """El ``Runtime`` de esta instancia — módulos, servicios, capacidades, eventos."""
        runtime: Runtime = self._asgi_app.state.runtime
        return runtime

    @property
    def version(self) -> str:
        """La versión de TEAF con la que se construyó esta aplicación."""
        return FRAMEWORK_VERSION

    @property
    def asgi(self) -> FastAPI:
        """La aplicación FastAPI subyacente — vía de escape para necesidades avanzadas
        (montar routers adicionales, un ``TestClient`` en pruebas) sin exponer
        ``teaf._internal.core.application`` como import directo."""
        return self._asgi_app


__all__ = ["Application"]
