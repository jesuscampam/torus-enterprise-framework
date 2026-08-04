"""Pruebas unitarias de cada fachada individual bajo teaf/ (importable por separado)."""

from __future__ import annotations

import importlib

import pytest

_FACADE_MODULES: dict[str, set[str]] = {
    "teaf.application": {"Application"},
    "teaf.runtime": {"Runtime"},
    "teaf.modules": {
        "Module",
        "ModuleBase",
        "ModuleBuilder",
        "ModuleCategory",
        "ModuleContext",
        "ModuleManifest",
        "ModuleRegistry",
    },
    "teaf.services": {"Lifetime", "ServiceContainer"},
    "teaf.events": {"Event", "EventBus"},
    "teaf.capabilities": {"CapabilityCategory", "CapabilityRegistry"},
    "teaf.health": {"Health"},
    "teaf.configuration": {"Configuration", "get_configuration"},
}


@pytest.mark.parametrize("module_name", sorted(_FACADE_MODULES))
def test_facade_module_all_matches_expected(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert set(module.__all__) == _FACADE_MODULES[module_name]


@pytest.mark.parametrize("module_name", sorted(_FACADE_MODULES))
def test_facade_module_importable_in_isolation(module_name: str) -> None:
    """Cada fachada se puede importar sola, sin pasar por teaf/__init__.py."""
    module = importlib.import_module(module_name)
    for name in module.__all__:
        assert hasattr(module, name)


def test_facades_do_not_import_each_other() -> None:
    """Ninguna fachada de teaf/ importa otra fachada de teaf/ — solo teaf/_internal/
    (ver docs/public-api/PACKAGE-STRUCTURE.md, sección 3).

    ``teaf._internal.*`` está deliberadamente excluido de esta prohibición:
    es la implementación privada (Sprint 2.6.2, ver ADR-006) que cada
    fachada sí debe importar. Lo prohibido es que una fachada importe *otra
    fachada hermana* (p. ej. ``teaf.application`` importando desde
    ``teaf.runtime``), no que importe su propia implementación interna.
    """
    import ast
    from pathlib import Path

    def _imports_another_facade(dotted: str) -> bool:
        return dotted.startswith("teaf.") and not dotted.startswith("teaf._internal")

    teaf_dir = Path(__file__).resolve().parents[2] / "teaf"
    for module_name in _FACADE_MODULES:
        file_path = teaf_dir / f"{module_name.removeprefix('teaf.')}.py"
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not _imports_another_facade(
                    node.module
                ), f"{file_path} importa de otra fachada teaf/ ({node.module})"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not _imports_another_facade(
                        alias.name
                    ), f"{file_path} importa de otra fachada teaf/ ({alias.name})"
