"""Pruebas unitarias de la Application Factory (backend/core/application.py)."""

from __future__ import annotations

from fastapi import FastAPI
from teaf._internal.config.settings import ProductionSettings, TestingSettings
from teaf._internal.core.application import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app(settings=TestingSettings())
    assert isinstance(app, FastAPI)


def test_create_app_registers_system_routes() -> None:
    app = create_app(settings=TestingSettings())
    paths = {getattr(route, "path", None) for route in app.routes}
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
