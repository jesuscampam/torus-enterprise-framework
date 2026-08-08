"""Pruebas unitarias de los comparadores de compatibilidad de backend/sdk/module_base.py.

``_satisfies_constraint``/``_parse_numeric_version`` son funciones privadas
del módulo — se prueban directamente porque encapsulan la única lógica
verdaderamente algorítmica de ``ModuleBase.bootstrap()`` (el resto es
orquestación ya cubierta por ``test_sdk_module_base.py``).
"""

from __future__ import annotations

import pytest
from teaf._internal.sdk.module_base import _parse_numeric_version, _satisfies_constraint


def test_parse_numeric_version_extracts_leading_digits() -> None:
    assert _parse_numeric_version("1.2.3") == (1, 2, 3)
    assert _parse_numeric_version("1.2.3-alpha") == (1, 2, 3)


def test_parse_numeric_version_defaults_to_zero_when_unparseable() -> None:
    assert _parse_numeric_version("not-a-version") == (0,)


@pytest.mark.parametrize("constraint", ["", "*"])
def test_satisfies_constraint_wildcard_always_true(constraint: str) -> None:
    assert _satisfies_constraint("0.1.0", constraint) is True


def test_satisfies_constraint_unparseable_constraint_defaults_true() -> None:
    # ModuleValidator ya rechazaría esto antes de llegar aquí en el flujo
    # real de bootstrap() — se prueba igualmente el comportamiento aislado.
    assert _satisfies_constraint("1.0.0", "not-a-constraint") is True


@pytest.mark.parametrize(
    ("actual", "constraint", "expected"),
    [
        ("1.0.0", "==1.0.0", True),
        ("1.0.1", "==1.0.0", False),
        ("1.0.0", "1.0.0", True),  # sin operador explícito == "=="
        ("1.5.0", ">=1.0.0", True),
        ("0.9.0", ">=1.0.0", False),
        ("1.0.0", "<=1.0.0", True),
        ("1.0.1", "<=1.0.0", False),
        ("2.0.0", ">1.0.0", True),
        ("1.0.0", ">1.0.0", False),
        ("0.5.0", "<1.0.0", True),
        ("1.0.0", "<1.0.0", False),
        ("1.2.5", "~=1.2", True),
        ("1.3.0", "~=1.2", False),
        ("0.5.0-alpha", ">=0.4", True),
    ],
)
def test_satisfies_constraint_operators(actual: str, constraint: str, expected: bool) -> None:
    assert _satisfies_constraint(actual, constraint) is expected


def test_satisfies_constraint_pads_shorter_version_with_zeros() -> None:
    assert _satisfies_constraint("1.0", ">=1.0.0") is True
    assert _satisfies_constraint("1", ">=1.0.0") is True
