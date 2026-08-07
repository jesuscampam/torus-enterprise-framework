"""Pruebas unitarias de la Application Factory (backend/core/application.py)."""

from __future__ import annotations

from fastapi import FastAPI
from teaf._internal.config.settings import ProductionSettings, TestingSettings
from teaf._internal.core.application import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app(settings=TestingSettings())
    assert isinstance(app, FastAPI)


def test_create_app_registers_system_routes() -> None:
    """Las rutas de sistema quedan registradas y publicadas en el esquema.

    Se comprueban sobre ``app.openapi()`` y no recorriendo ``app.routes``:
    desde FastAPI 0.141 / Starlette 1.4, ``include_router`` envuelve cada
    router en un ``_IncludedRouter`` en vez de aplanar sus rutas en
    ``app.routes``, así que recorrer esa lista ya no las ve (Sprint 3.0).
    El esquema, además, es el contrato observable: comprobarlo verifica que
    la ruta existe **y** que se publica, no solo lo primero.
    """
    paths = create_app(settings=TestingSettings()).openapi()["paths"]
    assert {"/", "/health", "/live", "/ready"}.issubset(paths)


def test_create_app_uses_app_name_as_title() -> None:
    settings = TestingSettings(app_name="Mi Framework")
    app = create_app(settings=settings)
    assert app.title == "Mi Framework"


def test_create_app_disables_docs_in_production() -> None:
    app = create_app(settings=ProductionSettings())
    assert app.docs_url is None
    assert app.redoc_url is None


def test_create_app_enables_docs_outside_production() -> None:
    app = create_app(settings=TestingSettings())
    assert app.docs_url == "/docs"
