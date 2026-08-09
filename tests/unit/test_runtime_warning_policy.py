"""La política de "``RuntimeWarning`` es error" está activa de verdad.

Nace del **3.0 Final Hardening**. TEAF es un framework asíncrono, y el modo
más silencioso de romperlo es olvidar un ``await``: Python emite
``RuntimeWarning: coroutine '...' was never awaited``, la corrutina no se
ejecuta nunca, y **la prueba pasa igual**. Un fallo así no lo detecta ninguna
aserción; solo lo detecta convertir ese warning en error.

La política vive en ``[tool.pytest.ini_options].filterwarnings`` de
``pyproject.toml`` para que ``python -m pytest`` a secas ya la aplique, sin
depender de que quien la ejecute recuerde ``-W error::RuntimeWarning``.

**Hacen falta dos filtros, no uno** — y se descubrió ejecutando una regresión
simulada, no razonando. Un ``await`` olvidado no llega como un
``RuntimeWarning`` corriente: lo emite el recolector de basura al destruir la
corrutina, así que viaja por el gancho de excepciones *unraisable* y pytest lo
envuelve en ``PytestUnraisableExceptionWarning``. Con solo
``error::RuntimeWarning``, el test que olvidaba el ``await`` **seguía pasando
en verde**. La cadena real es::

    await olvidado -> GC destruye la corrutina -> RuntimeWarning
      -> gancho unraisable -> PytestUnraisableExceptionWarning -> error -> FAIL

**Por qué no se prueba aquí con una corrutina sin await de verdad**: ese aviso
depende de *cuándo* el recolector destruye el objeto, momento que CPython no
garantiza y que difiere entre implementaciones. Meterlo en la suite sería
exactamente el "comportamiento frágil o dependiente del runtime" que hay que
evitar. Se comprueban en su lugar los dos mecanismos que lo hacen fallar, de
forma determinista; la comprobación extremo a extremo se hizo una vez, fuera de
la suite, y está documentada en ``CHANGELOG.md``.
"""

from __future__ import annotations

import tomllib
import warnings
from pathlib import Path

import pytest

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_a_runtime_warning_raises_instead_of_being_reported() -> None:
    """El comportamiento efectivo, no lo que diga la configuración.

    Si la política está activa, emitir un ``RuntimeWarning`` levanta la
    excepción en el punto de emisión. Es lo que convierte un ``await`` olvidado
    en un test rojo.
    """
    with pytest.raises(RuntimeWarning, match="política activa"):
        warnings.warn("comprobación de que la política activa", RuntimeWarning, stacklevel=1)


def test_the_policy_is_declared_in_pyproject_not_only_in_the_command_line() -> None:
    """Que esté declarada en el proyecto, no pasada a mano al invocar pytest.

    La prueba anterior pasaría igual si alguien hubiera lanzado la suite con
    ``-W error::RuntimeWarning`` desde fuera. Esta fija que la política forme
    parte del contrato reproducible del repositorio.
    """
    with _PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    options = pyproject["tool"]["pytest"]["ini_options"]  # type: ignore[index]
    assert "error::RuntimeWarning" in options["filterwarnings"]


def test_the_unraisable_filter_is_present_because_it_is_the_one_that_catches_await() -> None:
    """El filtro sin el que la política no sirve para lo que se creó.

    Es contraintuitivo y por eso tiene prueba propia: ``error::RuntimeWarning``
    **no** atrapa un ``await`` olvidado. El aviso lo emite el GC por el gancho
    *unraisable*, y pytest lo envuelve en ``PytestUnraisableExceptionWarning``.
    Sin esta segunda entrada, el test que olvida el ``await`` pasa en verde —
    comprobado con una regresión simulada durante el 3.0 Final Hardening.

    Si alguien la retira por parecer redundante con la anterior, esto lo para.
    """
    with _PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    filters = pyproject["tool"]["pytest"]["ini_options"]["filterwarnings"]  # type: ignore[index]
    assert "error::pytest.PytestUnraisableExceptionWarning" in filters


def test_no_filter_silences_runtime_warnings_anywhere() -> None:
    """Nadie ha añadido después un filtro que anule la política.

    ``filterwarnings`` se aplica en orden y el último que casa gana, así que un
    ``ignore::RuntimeWarning`` posterior desactivaría todo lo anterior sin que
    ninguna otra prueba lo notara.
    """
    with _PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    filters: list[str] = pyproject["tool"]["pytest"]["ini_options"]["filterwarnings"]  # type: ignore[index]
    silenced = [
        f
        for f in filters
        if f.startswith(("ignore", "default", "always")) and "RuntimeWarning" in f
    ]
    assert not silenced, f"filtros que silencian RuntimeWarning: {silenced}"
