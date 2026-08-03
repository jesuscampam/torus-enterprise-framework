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
    """Ninguna fachada de teaf/ importa otra fachada de teaf/ — solo backend/ (ver
    docs/public-api/PACKAGE-STRUCTURE.md, sección 3)."""
    import ast
    from pathlib import Path

    teaf_dir = Path(__file__).resolve().parents[2] / "teaf"
    for module_name in _FACADE_MODULES:
        file_path = teaf_dir / f"{module_name.removeprefix('teaf.')}.py"
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "teaf."
                ), f"{file_path} importa de otra fachada teaf/ ({node.module})"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        "teaf."
                    ), f"{file_path} importa de otra fachada teaf/ ({alias.name})"
