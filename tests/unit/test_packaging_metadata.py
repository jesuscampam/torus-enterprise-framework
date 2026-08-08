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


def test_pyproject_declares_every_supported_python_version_as_a_classifier() -> None:
    """Sprint 3.0.3: ganar 3.14 no puede costar 3.11-3.13.

    ``requires-python`` es lo que pip aplica; los clasificadores son lo que se
    publica y lo que lee un humano en PyPI. Aquí se fija la lista completa para
    que añadir o quitar una versión sea siempre un cambio explícito. La
    coherencia interna entre ambos campos la comprueba
    ``test_python_version_support.py``.
    """
    pyproject = _load_pyproject()
    classifiers: list[str] = pyproject["project"]["classifiers"]  # type: ignore[index,assignment]
    assert [c for c in classifiers if c.startswith("Programming Language :: Python ::")] == [
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ]


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


def test_every_runtime_dependency_is_pinned_exactly() -> None:
    """La política de [DEPENDENCIES.md](../../docs/DEPENDENCIES.md) —"versiones fijadas
    con ``==``, nunca rangos abiertos"— vivía solo en prosa, y nada la hacía cumplir.

    Sprint 3.0.3 la convierte en prueba. El motivo no es estético: el sprint nació
    porque una dependencia **transitiva** con código nativo no tenía wheel para
    Python 3.14, y se descubrió que ``starlette`` y ``greenlet`` entraban sin techo
    (``starlette>=0.46.0``, ``greenlet>=1``) y flotaban entre instalaciones del
    mismo commit. Un rango abierto en este fichero es una regresión silenciosa a
    ese estado.
    """
    requirements = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    unpinned = [
        line.strip()
        for line in requirements.splitlines()
        if line.strip() and not line.strip().startswith("#") and "==" not in line
    ]
    assert not unpinned, f"dependencias sin fijar con '==': {unpinned}"


def test_starlette_and_greenlet_stay_pinned_as_direct_dependencies() -> None:
    """Regresión concreta del Sprint 3.0.3.

    Ambas son transitivas —de ``fastapi`` y de ``sqlalchemy[asyncio]``— y ninguna
    aparecía en los manifiestos. Si alguien las retira por considerarlas
    "redundantes con lo que ya arrastra FastAPI", vuelve la deriva que este sprint
    cerró, y con ``greenlet`` además vuelve el riesgo de compilación nativa.
    """
    declared = set(_load_pyproject()["project"]["dependencies"])  # type: ignore[index]
    assert "starlette==1.4.1" in declared
    assert "greenlet==3.5.4" in declared


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
