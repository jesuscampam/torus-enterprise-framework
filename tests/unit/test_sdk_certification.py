"""Pruebas unitarias de backend/sdk/certification.py (ModuleCertification)."""

from __future__ import annotations

from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.certification import CERTIFICATION_SECTIONS, ModuleCertification
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


class _GoodModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id="demo", name="demo", display_name="Demo")
            .with_version("1.0.0")
            .with_documentation("docs/demo/DEMO.md")
            .add_capability(id="demo.cap", name="demo-cap")
            .add_healthcheck(name="demo.ping")
            .build()
        )


class _UndocumentedModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return ModuleBuilder(id="undocumented", name="undocumented").build()


class _InvalidModule(ModuleBase):
    def get_manifest(self) -> ModuleManifest:
        return ModuleBuilder(id="Bad Id!", name="").build()


def test_certification_sections_has_eight_entries() -> None:
    assert len(CERTIFICATION_SECTIONS) == 8
    assert ModuleCertification.describe_sections() == CERTIFICATION_SECTIONS


def test_well_formed_module_is_certified() -> None:
    result = ModuleCertification().certify(_GoodModule())

    assert result.certified is True
    assert all(result.checks.values())
    assert result.errors == ()


def test_undocumented_module_fails_documentation_check() -> None:
    result = ModuleCertification().certify(_UndocumentedModule())

    assert result.certified is False
    assert result.checks["documentation"] is False
    assert any("documentation" in e for e in result.errors)


def test_invalid_module_fails_specification_check() -> None:
    result = ModuleCertification().certify(_InvalidModule())

    assert result.certified is False
    assert result.checks["specification"] is False
    assert result.checks["metadata"] is False


def test_certification_result_as_dict_is_serializable() -> None:
    result = ModuleCertification().certify(_GoodModule())
    payload = result.as_dict()

    assert payload["certified"] is True
    assert isinstance(payload["checks"], dict)
    assert payload["errors"] == []
