"""Ejecuta cada ejemplo de examples/ como un proceso real y verifica su salida.

Más estricto que solo comprobar que no importan `backend.*` (ver
tests/unit/test_import_boundary_checker.py) — esto prueba que además
funcionan de extremo a extremo tal como los ejecutaría un desarrollador
siguiendo docs/public-api/ o examples/README.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
_EXAMPLE_DIRS = sorted(p for p in _EXAMPLES_DIR.iterdir() if (p / "main.py").exists())


@pytest.mark.parametrize("example_dir", _EXAMPLE_DIRS, ids=lambda p: p.name)
def test_example_runs_successfully(example_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=example_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_hello_world_prints_the_framework_version() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "hello-world",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "TEAF" in result.stdout
    assert "Runtime state: running" in result.stdout
    assert "Runtime state: stopped" in result.stdout


def test_basic_module_greets_and_registers_its_capability() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "basic-module",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Hola, TEAF." in result.stdout
    assert "Capacidad registrada: True" in result.stdout


def test_application_bootstrap_registers_the_clock_module() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "application-bootstrap",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Servicios registrados: 1" in result.stdout
    assert "Capacidades registradas: 1" in result.stdout


def test_discovered_at_least_the_three_expected_examples() -> None:
    names = {p.name for p in _EXAMPLE_DIRS}
    assert names == {"hello-world", "basic-module", "application-bootstrap"}
