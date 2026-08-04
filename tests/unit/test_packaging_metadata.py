"""Pruebas de empaquetado — pyproject.toml, requirements.txt e instalación real.

No vuelve a ejecutar ``pip install -e .`` (costoso, y modificaría el
entorno en cada corrida de la suite) — en su lugar, verifica que el
paquete ya instalado en modo editable (ver validación manual del Sprint)
coincide con lo declarado en el código fuente, y que ``pyproject.toml``
está bien formado.
"""

from __future__ import annotations

import re
import tomllib
from importlib.metadata import version as installed_version
from pathlib import Path

from teaf.version import FRAMEWORK_VERSION

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_pyproject() -> dict[str, object]:
    with (_REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_pyproject_declares_teaf_as_the_package_name() -> None:
    pyproject = _load_pyproject()
    assert pyproject["project"]["name"] == "teaf"  # type: ignore[index]


def test_pyproject_version_matches_framework_version() -> None:
    """Único punto de verdad: si alguien sube FRAMEWORK_VERSION sin actualizar
    pyproject.toml (o viceversa), esta prueba falla — ver
    docs/public-api/VERSIONING.md."""
    pyproject = _load_pyproject()
    assert pyproject["project"]["version"] == FRAMEWORK_VERSION  # type: ignore[index]


def test_pyproject_requires_python_311_or_newer() -> None:
    pyproject = _load_pyproject()
    assert pyproject["project"]["requires-python"] == ">=3.11"  # type: ignore[index]


def test_pyproject_has_a_build_system() -> None:
    pyproject = _load_pyproject()
    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"  # type: ignore[index]


def test_pyproject_declares_no_cli_entry_points() -> None:
    """Sprint 2.5.1, sección 13 (NO IMPLEMENTAR): sin CLI todavía."""
    pyproject = _load_pyproject()
    project = pyproject["project"]
    assert "scripts" not in project  # type: ignore[operator]


def test_pyproject_package_discovery_includes_only_teaf() -> None:
    """Sprint 2.6.2: `backend*` desaparece — `teaf._internal` es subpaquete de `teaf`."""
    pyproject = _load_pyproject()
    include = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]  # type: ignore[index]
    assert include == ["teaf*"]


def test_pyproject_dependencies_match_requirements_txt() -> None:
    """Ambos archivos fijan las mismas versiones exactas (ver comentario en pyproject.toml)."""
    pyproject = _load_pyproject()
    declared = set(pyproject["project"]["dependencies"])  # type: ignore[index]

    requirements_text = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    from_requirements = {
        line.strip()
        for line in requirements_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert declared == from_requirements


def test_teaf_is_installed_as_an_editable_distribution_matching_source() -> None:
    """Confirma que ``pip install -e .`` (ejecutado como parte de la validación del
    Sprint) instaló la misma versión que declara el código fuente — no una copia
    obsoleta."""
    assert installed_version("teaf") == _normalize(FRAMEWORK_VERSION)


def _normalize(version: str) -> str:
    """PEP 440 normaliza ``-alpha`` a ``a0`` — ``importlib.metadata`` devuelve la
    forma normalizada, no el literal de ``pyproject.toml``/``teaf.version``."""
    match = re.match(r"^(\d+(?:\.\d+)*)-alpha$", version)
    if match is None:
        return version
    return f"{match.group(1)}a0"


def test_teaf_has_a_py_typed_marker() -> None:
    """PEP 561 — TEAF distribuye sus propias anotaciones de tipo (ver
    docs/public-api/PACKAGE-STRUCTURE.md, sección 6)."""
    assert (_REPO_ROOT / "teaf" / "py.typed").exists()
