"""Lista de comprobación de compatibilidad con Windows, como código.

El bug que motivó este archivo: ``teaf/_internal/runtime/runtime.py``
importaba ``resource`` —módulo estándar de POSIX, inexistente en
Windows— a nivel de módulo. Como ``ModuleContext``/``Runtime`` están en la
cadena de import de ``from teaf import Application``, cualquier aplicación
que solo intentara importar TEAF en Windows fallaba con
``ModuleNotFoundError`` antes de escribir una sola línea propia.

La corrección aísla esa dependencia detrás de
``teaf._internal.runtime.process_metrics`` (ver
``tests/unit/test_process_metrics_platform.py`` para las pruebas
específicas de esa pieza). Este archivo comprueba la consecuencia práctica:
que el camino completo —importar, construir, arrancar, servir HTTP,
apagar— ya no depende de ninguna API exclusiva de POSIX. No usa
``sys.platform`` ni marcadores de plataforma porque, tras la corrección,
nada de este camino se ramifica por plataforma: es exactamente la misma
prueba en Linux y en Windows.

**Import** usa exclusivamente ``from teaf import ...`` — la API pública,
igual que la usaría ``teaf-reference-app`` — para que esta prueba verifique
lo mismo que verificaría una aplicación real.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf import Application, Runtime
from teaf._internal.runtime.runtime import RuntimeState


def test_public_import_succeeds() -> None:
    """Equivalente a ``from teaf import Application`` — si esto falla con
    ``ModuleNotFoundError: resource``, el patch no está aplicado."""
    assert Application is not None


def test_application_constructs_and_exposes_the_asgi_app() -> None:
    app = Application()
    assert isinstance(app.asgi, FastAPI)


def test_runtime_reaches_running_then_stopped() -> None:
    """Ciclo de vida completo: bootstrapping -> running -> stopped.

    Entrar y salir del ``TestClient`` como gestor de contexto es lo que
    dispara el ``lifespan`` ASGI (``startup``/``shutdown``) — el mismo
    mecanismo que usa uvicorn en producción, sin necesitar servidor real.
    """
    app = Application()
    runtime = app.runtime
    assert isinstance(runtime, Runtime)
    assert runtime.state is RuntimeState.BOOTSTRAPPING

    with TestClient(app):
        running_state = runtime.state

    assert running_state is RuntimeState.RUNNING
    assert runtime.state is RuntimeState.STOPPED


def test_system_endpoints_respond() -> None:
    """El contrato HTTP actual de sistema — ver ``monitoring/README.md``."""
    app = Application()
    with TestClient(app) as client:
        for path in ("/", "/health", "/info", "/runtime/info"):
            response = client.get(path)
            assert response.status_code == 200, f"{path} devolvió {response.status_code}"
