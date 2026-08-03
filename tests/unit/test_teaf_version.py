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
