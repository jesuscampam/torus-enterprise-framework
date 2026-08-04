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
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.types import Receive, Scope, Send

from teaf._internal.config.settings import Settings
from teaf._internal.core.application import FRAMEWORK_VERSION, create_app
from teaf._internal.runtime.runtime import Runtime


class Application:
    """Fachada pública de una aplicación TEAF en ejecución."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Construye la aplicación. ``settings=None`` resuelve la configuración del entorno."""
        self._asgi_app: FastAPI = create_app(settings)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Interfaz ASGI — permite servir una instancia directamente (``uvicorn app:app``)."""
        await self._asgi_app(scope, receive, send)

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
