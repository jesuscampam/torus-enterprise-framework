"""Pruebas unitarias de teaf/version.py — el único punto de verdad de versión."""

from __future__ import annotations

from teaf.version import (
    CURRENT_VERSION,
    FRAMEWORK_VERSION,
    MODULE_SPEC_VERSION,
    PUBLIC_API_VERSION,
    RUNTIME_VERSION,
    SDK_VERSION,
    Version,
    is_compatible,
)


def test_the_five_constants_are_non_empty_strings() -> None:
    for value in (
        FRAMEWORK_VERSION,
        SDK_VERSION,
        RUNTIME_VERSION,
        MODULE_SPEC_VERSION,
        PUBLIC_API_VERSION,
    ):
        assert isinstance(value, str)
        assert value


def test_current_version_matches_the_five_constants() -> None:
    assert CURRENT_VERSION.framework == FRAMEWORK_VERSION
    assert CURRENT_VERSION.sdk == SDK_VERSION
    assert CURRENT_VERSION.runtime == RUNTIME_VERSION
    assert CURRENT_VERSION.module_spec == MODULE_SPEC_VERSION
    assert CURRENT_VERSION.public_api == PUBLIC_API_VERSION


def test_current_version_is_a_version_instance() -> None:
    assert isinstance(CURRENT_VERSION, Version)


def test_as_dict_is_fully_serializable() -> None:
    payload = CURRENT_VERSION.as_dict()
    assert payload == {
        "framework": FRAMEWORK_VERSION,
        "sdk": SDK_VERSION,
        "runtime": RUNTIME_VERSION,
        "moduleSpec": MODULE_SPEC_VERSION,
        "publicApi": PUBLIC_API_VERSION,
    }


def test_is_compatible_wildcard_and_empty_always_true() -> None:
    assert is_compatible("0.1.0", "*") is True
    assert is_compatible("0.1.0", "") is True


def test_is_compatible_exact_match() -> None:
    assert is_compatible("1.2.3", "1.2.3") is True
    assert is_compatible("1.2.3", "==1.2.3") is True
    assert is_compatible("1.2.4", "1.2.3") is False


def test_is_compatible_greater_equal() -> None:
    assert is_compatible("1.5.0", ">=1.2") is True
    assert is_compatible("1.0.0", ">=1.2") is False


def test_is_compatible_less_equal() -> None:
    assert is_compatible("1.0.0", "<=1.2") is True
    assert is_compatible("1.5.0", "<=1.2") is False


def test_is_compatible_strict_greater_and_less() -> None:
    assert is_compatible("2.0.0", ">1.0") is True
    assert is_compatible("1.0.0", ">1.0") is False
    assert is_compatible("0.5.0", "<1.0") is True
    assert is_compatible("1.0.0", "<1.0") is False


def test_is_compatible_compatible_release_operator() -> None:
    assert is_compatible("1.2.5", "~=1.2") is True
    assert is_compatible("1.3.0", "~=1.2") is False
    assert is_compatible("1.1.9", "~=1.2") is False


def test_is_compatible_ignores_prerelease_suffix() -> None:
    assert is_compatible("0.6.1-alpha", ">=0.5") is True
    assert is_compatible("0.6.1-alpha", ">=0.7") is False


def test_is_compatible_unrecognized_constraint_is_permissive() -> None:
    assert is_compatible("1.0.0", "not-a-real-constraint") is True


def test_is_compatible_pads_missing_version_segments() -> None:
    assert is_compatible("2.0", ">=1.9.9") is True


def test_is_compatible_treats_non_numeric_version_as_zero() -> None:
    """Una versión sin parte numérica reconocible se trata como ``0`` — nunca lanza."""
    assert is_compatible("unreleased", ">=1.0") is False
    assert is_compatible("unreleased", "*") is True


def test_teaf_exposes_dunder_version() -> None:
    """``import teaf; teaf.__version__`` es lo primero que prueba cualquier
    herramienta del ecosistema (pip, poetry, un script de release, un `--version`
    de una app consumidora).

    Hasta el 3.0 Final Hardening no existía: la versión solo se alcanzaba por
    ``teaf.Version.framework`` o ``teaf.version.FRAMEWORK_VERSION``, ambas
    correctas pero ninguna convencional.
    """
    import teaf

    assert hasattr(teaf, "__version__")
    assert isinstance(teaf.__version__, str)
    assert teaf.__version__


def test_dunder_version_is_an_alias_of_the_canonical_source_not_a_copy() -> None:
    """El literal de versión vive en un único sitio.

    ``teaf.__version__`` debe *derivar* de ``FRAMEWORK_VERSION`` —que a su vez
    nace en ``teaf/_internal/core/application.py``—, no repetirlo. Si alguien
    escribe el número a mano en ``teaf/__init__.py``, esto lo detecta en cuanto
    las dos fuentes divergen.
    """
    import teaf

    assert teaf.__version__ == FRAMEWORK_VERSION
    assert teaf.__version__ == CURRENT_VERSION.framework
    assert teaf.__version__ == teaf.Version.framework


def test_dunder_version_matches_the_installed_package_metadata() -> None:
    """Coherencia con lo que ve el gestor de paquetes.

    ``importlib.metadata`` devuelve la forma normalizada de PEP 440 (``0.10.3a0``
    para ``0.10.3-alpha``), así que se compara normalizando, no literalmente.
    """
    import re
    from importlib.metadata import version as installed_version

    import teaf

    def normalize(raw: str) -> str:
        match = re.match(r"^(\d+(?:\.\d+)*)-alpha$", raw)
        return f"{match.group(1)}a0" if match else raw

    assert installed_version("teaf") == normalize(teaf.__version__)


def test_dunder_version_is_deliberately_absent_from_all() -> None:
    """``__all__`` enumera símbolos importables, no metadatos del módulo.

    ``from teaf import *`` no debe arrastrar ``__version__`` —Python ya excluye
    los dunder de la importación con asterisco—, y meterlo en ``__all__`` haría
    fallar ``test_teaf_package.py``, que fija la superficie pública exacta.
    """
    import teaf

    assert "__version__" not in teaf.__all__
