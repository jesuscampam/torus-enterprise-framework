"""Pruebas de integración de teaf.Application — la fachada pública de aplicación.

Usa ``TestingSettings`` (interno) solo para construir una instancia
determinista — el resto de la prueba interactúa exclusivamente con la
superficie pública de ``Application`` (``.asgi``, ``.runtime``, ``.version``,
el propio callable ASGI), igual que haría un consumidor externo.
"""

from __future__ import annotations

import httpx
import pytest
from backend.config.settings import TestingSettings
from fastapi import FastAPI
from teaf import Application, Runtime
from teaf.version import FRAMEWORK_VERSION


@pytest.fixture
def app() -> Application:
    return Application(TestingSettings())


def test_application_exposes_the_underlying_fastapi_instance(app: Application) -> None:
    assert isinstance(app.asgi, FastAPI)


def test_application_exposes_a_runtime_instance(app: Application) -> None:
    assert isinstance(app.runtime, Runtime)


def test_application_version_matches_teaf_version(app: Application) -> None:
    assert app.version == FRAMEWORK_VERSION


def test_application_is_a_valid_asgi_callable() -> None:
    async def scenario() -> httpx.Response:
        app = Application(TestingSettings())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            return await http_client.get("/health")

    import asyncio

    response = asyncio.run(scenario())
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_application_default_settings_resolve_without_explicit_configuration() -> None:
    """``Application()`` sin argumentos resuelve la configuración del entorno (igual que
    ``create_app()``) — no exige que el consumidor construya ``Configuration`` a mano."""
    app = Application()
    assert isinstance(app.asgi, FastAPI)
