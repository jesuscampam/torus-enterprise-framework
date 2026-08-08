"""Pruebas del Sprint 2.6.2 (Internal Namespace Refactor) — verifica que
``backend`` desapareció por completo y que ``teaf._internal`` funciona como
su reemplazo, sin afectar la superficie pública."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import teaf
from scripts.check_public_api_boundary import check_paths


def test_backend_top_level_package_no_longer_exists() -> None:
    assert importlib.util.find_spec("backend") is None


def test_teaf_internal_exists_and_is_importable() -> None:
    assert importlib.util.find_spec("teaf._internal") is not None

    import teaf._internal.core.application  # noqa: F401


def test_no_backend_imports_anywhere_in_repository() -> None:
    """Ningún archivo .py del repositorio importa el namespace legado ``backend``."""
    repository_root = Path(__file__).resolve().parents[2]
    scan_roots = [
        repository_root / "teaf",
        repository_root / "tests",
        repository_root / "scripts",
        repository_root / "database",
        repository_root / "examples",
    ]
    violations = check_paths(scan_roots, forbidden=("backend",))
    assert violations == []


def test_public_api_still_works_after_refactor() -> None:
    """Regresión: la superficie pública no cambió con el movimiento de backend/."""
    app = teaf.Application()
    assert app.version is not None
    assert app.runtime is not None
