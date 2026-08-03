"""Fixtures compartidas por toda la suite de pruebas.

Usa ``TestingSettings`` explícita en vez de depender de variables de
entorno globales — mantiene las pruebas deterministas y aisladas entre sí.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from backend.config.settings import TestingSettings
from backend.core.application import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    """Instancia de la aplicación construida con configuración de pruebas."""
    return create_app(settings=TestingSettings())


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Cliente HTTP de pruebas contra la aplicación de referencia."""
    with TestClient(app) as test_client:
        yield test_client
