"""Pruebas unitarias de backend/sdk/validator.py (ModuleValidator)."""

from __future__ import annotations

import pytest
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.descriptor import ModuleDescriptor
from teaf._internal.sdk.exceptions import ModuleValidationException
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.validator import ModuleValidationResult, ModuleValidator


class _Greeter:
    pass


class _OtherGreeter:
    pass


def _valid_manifest() -> ModuleManifest:
    return ModuleBuilder(id="demo", name="demo", display_name="Demo").with_version("1.0.0").build()


def test_valid_manifest_passes() -> None:
    result = ModuleValidator().validate(_valid_manifest())
    assert result.valid is True
    assert result.errors == ()


def test_invalid_id_is_rejected() -> None:
    manifest = ModuleBuilder(id="Bad Id!", name="demo", display_name="Demo").build()
    result = ModuleValidator().validate(manifest)
    assert result.valid is False
    assert any("id" in e for e in result.errors)


def test_empty_name_is_rejected() -> None:
    manifest = ModuleBuilder(id="demo", name="", display_name="Demo").build()
    result = ModuleValidator().validate(manifest)
    assert any("name" in e for e in result.errors)


def test_empty_display_name_is_rejected() -> None:
    # ModuleBuilder sustituye display_name="" por 'name' (ver with_display_name),
    # así que para probar esta regla se construye el manifiesto directamente.
    descriptor = ModuleDescriptor(id="demo", name="demo", display_name="", version="0.0.0")
    manifest = ModuleManifest(descriptor=descriptor)
    result = ModuleValidator().validate(manifest)
    assert any("display_name" in e for e in result.errors)


def test_invalid_version_is_rejected() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_version("not-a-version").build()
    result = ModuleValidator().validate(manifest)
    assert any("version" in e for e in result.errors)


@pytest.mark.parametrize("version", ["1.0.0", "0.5.0-alpha", "10.20.30"])
def test_valid_version_formats_pass(version: str) -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_version(version).build()
    result = ModuleValidator().validate(manifest)
    assert result.valid is True


def test_self_dependency_is_rejected() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").add_dependency(module_id="demo").build()
    result = ModuleValidator().validate(manifest)
    assert any("depende de sí mismo" in e for e in result.errors)


def test_duplicate_dependency_is_rejected() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_dependency(module_id="core")
        .add_dependency(module_id="core")
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert any("declarado más de una vez" in e for e in result.errors)


def test_duplicate_capability_id_is_rejected() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_capability(id="dup", name="a")
        .add_capability(id="dup", name="b")
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert any("capabilities" in e for e in result.errors)


def test_duplicate_configuration_key_is_rejected() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_configuration(key="LEVEL")
        .add_configuration(key="LEVEL")
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert any("configuration" in e for e in result.errors)


def test_duplicate_service_contract_is_rejected() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_service(_Greeter, lambda c: _Greeter())
        .add_service(_Greeter, lambda c: _Greeter())
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert any("services" in e for e in result.errors)


def test_distinct_service_contracts_are_allowed() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_service(_Greeter, lambda c: _Greeter())
        .add_service(_OtherGreeter, lambda c: _OtherGreeter())
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert result.valid is True


def test_empty_healthcheck_name_is_rejected() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").add_healthcheck(name="").build()
    result = ModuleValidator().validate(manifest)
    assert any("health" in e for e in result.errors)


def test_duplicate_healthcheck_name_is_rejected() -> None:
    manifest = (
        ModuleBuilder(id="demo", name="demo")
        .add_healthcheck(name="ping")
        .add_healthcheck(name="ping")
        .build()
    )
    result = ModuleValidator().validate(manifest)
    assert any("nombre duplicado" in e for e in result.errors)


@pytest.mark.parametrize("constraint", ["nonsense", "1.0.0.0.0"])
def test_invalid_compatibility_constraint_is_rejected(constraint: str) -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_runtime_compatibility(constraint).build()
    result = ModuleValidator().validate(manifest)
    assert any("runtime_compatibility" in e for e in result.errors)


def test_invalid_sdk_compatibility_constraint_is_rejected() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_sdk_compatibility("nonsense").build()
    result = ModuleValidator().validate(manifest)
    assert any("sdk_compatibility" in e for e in result.errors)


@pytest.mark.parametrize("constraint", ["*", ">=1.0", "1.0.0", "~=1.2"])
def test_valid_compatibility_constraints_pass(constraint: str) -> None:
    manifest = ModuleBuilder(id="demo", name="demo").with_sdk_compatibility(constraint).build()
    result = ModuleValidator().validate(manifest)
    assert result.valid is True


def test_validate_or_raise_raises_on_invalid_manifest() -> None:
    manifest = ModuleBuilder(id="Bad!", name="").build()
    with pytest.raises(ModuleValidationException):
        ModuleValidator().validate_or_raise(manifest)


def test_validate_or_raise_does_not_raise_on_valid_manifest() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").build()
    ModuleValidator().validate_or_raise(manifest)  # no debe lanzar


def test_errors_by_section_groups_by_prefix() -> None:
    manifest = (
        ModuleBuilder(id="Bad!", name="demo")
        .add_capability(id="dup", name="a")
        .add_capability(id="dup", name="b")
        .build()
    )
    grouped = ModuleValidator().errors_by_section(manifest)
    assert "metadata" in grouped
    assert "capabilities" in grouped
    assert all("metadata" in e for e in grouped["metadata"])


def test_errors_by_section_empty_for_valid_manifest() -> None:
    manifest = ModuleBuilder(id="demo", name="demo").build()
    assert ModuleValidator().errors_by_section(manifest) == {}


def test_module_validation_result_as_dict() -> None:
    result = ModuleValidationResult(valid=False, errors=("metadata: x inválido.",))
    assert result.as_dict() == {"valid": False, "errors": ["metadata: x inválido."]}
