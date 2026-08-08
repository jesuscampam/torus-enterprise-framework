"""Coherencia entre las versiones de Python que TEAF **dice** soportar y las que soporta.

Nace del Sprint 3.0.3 (compatibilidad con Python 3.14). El defecto que lo
motivó no estaba en el código de TEAF —que no usa ninguna API retirada en
3.13/3.14— sino en tres dependencias fijadas a versiones sin soporte para
3.14. Un fallo así no lo detecta ninguna prueba de comportamiento: la suite
entera pasa en la versión de Python en la que se ejecuta, y falla al
*instalar* en otra.

Lo que sí se puede fijar aquí, y es lo que hace este archivo, es que la
**metadata no mienta**: que ``requires-python`` y los clasificadores digan lo
mismo, y que el intérprete que está ejecutando la suite esté dentro de lo
declarado. Si alguien sube el suelo de Python sin tocar los clasificadores
—o al revés— esto falla.

La comprobación de que las *dependencias* tienen wheel para cada versión
soportada no se puede hacer aquí sin salir a la red en cada ejecución; vive
en [PLATFORM-COMPATIBILITY.md](../../docs/PLATFORM-COMPATIBILITY.md) y en la
matriz de verificación manual del sprint.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pyproject() -> dict[str, object]:
    with _PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def _declared_versions() -> list[tuple[int, int]]:
    """Versiones ``3.x`` que declaran los clasificadores, como tuplas ordenadas."""
    project: dict[str, object] = _pyproject()["project"]  # type: ignore[assignment]
    classifiers: list[str] = project["classifiers"]  # type: ignore[assignment]
    found = []
    for classifier in classifiers:
        match = re.fullmatch(r"Programming Language :: Python :: (3)\.(\d+)", classifier)
        if match:
            found.append((int(match.group(1)), int(match.group(2))))
    return sorted(found)


def _requires_python_floor() -> tuple[int, int]:
    project: dict[str, object] = _pyproject()["project"]  # type: ignore[assignment]
    requires: str = project["requires-python"]  # type: ignore[assignment]
    match = re.fullmatch(r">=(\d+)\.(\d+)", requires.strip())
    assert match is not None, f"forma de requires-python no reconocida: {requires!r}"
    return int(match.group(1)), int(match.group(2))


def test_classifiers_declare_a_contiguous_range_of_python_versions() -> None:
    """Un hueco (p. ej. declarar 3.11 y 3.13 pero no 3.12) casi siempre es un
    despiste al añadir una versión, no una decisión."""
    versions = _declared_versions()
    assert versions, "ningún clasificador 'Programming Language :: Python :: 3.x'"
    minors = [minor for _, minor in versions]
    assert minors == list(
        range(minors[0], minors[-1] + 1)
    ), f"faltan versiones intermedias en los clasificadores: {minors}"


def test_the_lowest_classifier_matches_the_requires_python_floor() -> None:
    """``requires-python`` es lo que pip respeta; los clasificadores son lo que
    lee un humano. Si discrepan, uno de los dos engaña."""
    assert _declared_versions()[0] == _requires_python_floor()


def test_python_314_is_declared_as_supported() -> None:
    """Regresión del Sprint 3.0.3: si alguien retira 3.14 de los clasificadores,
    que sea una decisión explícita y no un descuido."""
    assert (3, 14) in _declared_versions()


def test_python_313_support_is_not_dropped() -> None:
    """El sprint exige expresamente no perder 3.13 al ganar 3.14."""
    assert (3, 13) in _declared_versions()


def test_the_running_interpreter_is_within_the_declared_range() -> None:
    """La suite se ejecuta en 3.11, 3.13 y 3.14 durante la validación del
    sprint; en las tres, el intérprete debe caer dentro de lo declarado."""
    running = sys.version_info[:2]
    declared = _declared_versions()
    assert (
        running >= _requires_python_floor()
    ), f"el intérprete {running} está por debajo de requires-python"
    assert running <= declared[-1], (
        f"el intérprete {running} es más nuevo que la última versión declarada "
        f"{declared[-1]} — añada el clasificador si de verdad está soportada"
    )
