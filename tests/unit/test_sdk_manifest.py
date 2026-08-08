"""Pruebas unitarias de backend/sdk/manifest.py y backend/sdk/specification.py."""

from __future__ import annotations

from teaf._internal.sdk.descriptor import ModuleDescriptor
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.specification import (
    CURRENT_SPECIFICATION,
    SPEC_VERSION,
    ModuleSpecification,
    ModuleSpecificationSection,
)


def test_manifest_as_dict_flattens_descriptor_fields() -> None:
    descriptor = ModuleDescriptor(id="demo", name="demo", display_name="Demo", version="0.1.0")
    manifest = ModuleManifest(descriptor=descriptor, license="MIT")

    payload = manifest.as_dict()

    assert payload["id"] == "demo"
    assert payload["displayName"] == "Demo"
    assert payload["license"] == "MIT"
    assert payload["capabilities"] == []
    assert payload["services"] == []
    assert payload["dependencies"] == []
    assert payload["configuration"] == []
    assert payload["healthChecks"] == []
    assert payload["events"] == []
    assert payload["runtimeCompatibility"] == "*"
    assert payload["sdkCompatibility"] == "*"


def test_module_specification_has_ten_sections() -> None:
    assert len(CURRENT_SPECIFICATION.sections) == 10
    assert CURRENT_SPECIFICATION.version == SPEC_VERSION


def test_module_specification_describe_is_serializable() -> None:
    spec = ModuleSpecification()
    payload = spec.describe()
    sections = payload["sections"]
    assert isinstance(sections, list)
    assert payload["version"] == "1.0"
    assert ModuleSpecificationSection.METADATA.value in sections
    assert ModuleSpecificationSection.VALIDATION_RULES.value in sections
