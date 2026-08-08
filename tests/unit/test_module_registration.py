"""Pruebas de la Module Registration API (Sprint 2.6.3).

Verifica que registrar módulos usando exclusivamente ``teaf.Application``
(``modules=[...]`` en el constructor y/o ``.add_module()``) arranca esos
módulos automáticamente cuando arranca el ciclo de vida ASGI — sin que el
consumidor llame a ``bootstrap()``, use ``asyncio.run()`` ni threads. El
ciclo de vida se dispara con ``TestClient`` (como ya hace ``tests/conftest.py``),
nunca con ``await app.runtime.startup()`` directo, porque el bootstrap de
módulos vive en el ``_lifespan`` del composition root, no en ``Runtime``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from teaf import (
    Application,
    CapabilityCategory,
    Module,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
)
from teaf._internal.config.settings import TestingSettings
from teaf._internal.sdk.exceptions import ModuleRegistrationException, ModuleValidationException
from teaf._internal.sdk.lifecycle import ModuleLifecycleState


def _manifest(module_id: str, *, capability: bool = False) -> ModuleManifest:
    builder = (
        ModuleBuilder(id=module_id, name=module_id, display_name=module_id.title())
        .with_version("1.0.0")
        .with_category(ModuleCategory.GENERIC)
    )
    if capability:
        builder = builder.add_capability(
            id=f"{module_id}.ping", name=f"{module_id}-ping", category=CapabilityCategory.UTILITY
        )
    return builder.build()


class _RecordingModule(Module):
    """Módulo mínimo que registra en ``order`` cuándo se lo arrancó/apagó."""

    def __init__(self, module_id: str, order: list[str], *, with_capability: bool = False) -> None:
        super().__init__()
        self._id = module_id
        self._order = order
        self._with_capability = with_capability

    def get_manifest(self) -> ModuleManifest:
        return _manifest(self._id, capability=self._with_capability)

    def register(self, context: ModuleContext) -> None:
        self._order.append(f"register:{self._id}")

    def stop(self, context: ModuleContext) -> None:
        self._order.append(f"stop:{self._id}")


class _InvalidManifestModule(Module):
    """Manifiesto inválido (id con mayúsculas) — dispara ``ModuleValidationException``."""

    def get_manifest(self) -> ModuleManifest:
        return ModuleBuilder(id="Invalid ID", name="x", display_name="X").build()


def _app(*, modules: list[Module] | None = None) -> Application:
    return Application(TestingSettings(), modules=modules)


# -- Application() / Application(modules=...) ---------------------------------


def test_application_without_modules_has_no_pending_modules() -> None:
    app = _app()
    assert app.asgi.state.pending_modules == []


def test_application_with_empty_modules_list_has_no_pending_modules() -> None:
    app = _app(modules=[])
    assert app.asgi.state.pending_modules == []


def test_application_with_one_module_stores_it_as_pending_before_startup() -> None:
    order: list[str] = []
    module = _RecordingModule("solo", order)
    app = _app(modules=[module])
    assert app.asgi.state.pending_modules == [module]
    assert order == []  # todavía no arrancó — recién al entrar en el lifespan


def test_application_bootstraps_single_module_on_lifespan_start() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("solo", order)])
    with TestClient(app.asgi):
        assert order == ["register:solo"]
        assert "solo" in {m.name for m in app.runtime.modules}


def test_no_manual_bootstrap_call_is_required() -> None:
    """El propio test nunca llama a ``.bootstrap()`` — solo pasa el módulo a ``Application``."""
    order: list[str] = []
    module = _RecordingModule("auto", order)
    app = _app(modules=[module])
    with TestClient(app.asgi):
        assert module.lifecycle.state is ModuleLifecycleState.READY


# -- Múltiples módulos / orden --------------------------------------------------


def test_multiple_modules_all_registered_via_constructor() -> None:
    order: list[str] = []
    app = _app(
        modules=[
            _RecordingModule("uno", order),
            _RecordingModule("dos", order),
            _RecordingModule("tres", order),
        ]
    )
    with TestClient(app.asgi):
        names = {m.name for m in app.runtime.modules}
        assert {"uno", "dos", "tres"} <= names


def test_modules_bootstrap_in_registration_order() -> None:
    order: list[str] = []
    app = _app(
        modules=[
            _RecordingModule("uno", order),
            _RecordingModule("dos", order),
            _RecordingModule("tres", order),
        ]
    )
    with TestClient(app.asgi):
        assert order == ["register:uno", "register:dos", "register:tres"]


def test_modules_shutdown_in_reverse_registration_order() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("uno", order), _RecordingModule("dos", order)])
    with TestClient(app.asgi):
        pass
    assert order == ["register:uno", "register:dos", "stop:dos", "stop:uno"]


# -- .add_module() fluido -------------------------------------------------------


def test_add_module_returns_self_for_chaining() -> None:
    order: list[str] = []
    app = _app()
    result = app.add_module(_RecordingModule("a", order))
    assert result is app


def test_add_module_fluent_chain_registers_all_modules() -> None:
    order: list[str] = []
    app = _app().add_module(_RecordingModule("a", order)).add_module(_RecordingModule("b", order))
    with TestClient(app.asgi):
        names = {m.name for m in app.runtime.modules}
        assert {"a", "b"} <= names
    assert order == ["register:a", "register:b", "stop:b", "stop:a"]


def test_add_module_after_constructor_modules_preserves_order() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("first", order)])
    app.add_module(_RecordingModule("second", order))
    with TestClient(app.asgi):
        pass
    assert order == ["register:first", "register:second", "stop:second", "stop:first"]


# -- Integración con Runtime / CapabilityRegistry --------------------------------


def test_module_registered_via_application_appears_in_runtime_modules() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("visible", order)])
    with TestClient(app.asgi):
        assert any(m.name == "visible" for m in app.runtime.modules)


def test_capability_declared_in_manifest_is_registered_via_application() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("caps", order, with_capability=True)])
    with TestClient(app.asgi):
        assert app.runtime.capability_registry.exists("caps.ping")


# -- Errores de registro / duplicados --------------------------------------------


def test_duplicate_module_ids_raise_module_registration_exception() -> None:
    order: list[str] = []
    app = _app(modules=[_RecordingModule("dup", order), _RecordingModule("dup", order)])
    with pytest.raises(ModuleRegistrationException):
        with TestClient(app.asgi):
            pass


def test_invalid_manifest_raises_module_validation_exception() -> None:
    app = _app(modules=[_InvalidManifestModule()])
    with pytest.raises(ModuleValidationException):
        with TestClient(app.asgi):
            pass


# -- Lifecycle --------------------------------------------------------------------


def test_module_lifecycle_reaches_ready_after_automatic_bootstrap() -> None:
    order: list[str] = []
    module = _RecordingModule("cycle", order)
    app = _app(modules=[module])
    with TestClient(app.asgi):
        assert module.lifecycle.state is ModuleLifecycleState.READY


def test_module_lifecycle_reaches_disposed_after_application_shutdown() -> None:
    order: list[str] = []
    module = _RecordingModule("cycle2", order)
    app = _app(modules=[module])
    with TestClient(app.asgi):
        pass
    assert module.lifecycle.state is ModuleLifecycleState.DISPOSED


# -- No rompe el flujo existente sin módulos -------------------------------------


def test_application_without_modules_still_serves_health_endpoint() -> None:
    app = _app()
    with TestClient(app.asgi) as client:
        response = client.get("/health")
        assert response.status_code == 200
