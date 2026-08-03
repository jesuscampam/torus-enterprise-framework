"""Pruebas unitarias de backend/runtime/manifest.py (Runtime Manifest)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from backend.runtime.capabilities.builder import CapabilityBuilder
from backend.runtime.manifest import (
    KNOWN_CONTRACTS,
    KNOWN_FACTORIES,
    KNOWN_PROVIDERS,
    generate_manifest,
    write_manifest,
)
from backend.runtime.runtime import Runtime


def _running_runtime() -> Runtime:
    registry = ModuleRegistry()
    registry.register(ModuleDescriptor(name="ai", version="1", status=ModuleStatus.CONTRACTS_ONLY))
    runtime = Runtime(registry=registry, framework_version="0.4.0-alpha")
    asyncio.run(runtime.startup())
    return runtime


def test_generate_manifest_contains_all_required_sections() -> None:
    runtime = _running_runtime()

    manifest = generate_manifest(runtime, configuration_summary={"env": "test"})

    assert manifest["framework"] == "TEAF"
    assert manifest["version"] == "0.4.0-alpha"
    assert isinstance(manifest["runtime"], dict)
    assert manifest["modules"] == [module.as_dict() for module in runtime.modules]
    assert manifest["capabilities"] == []
    assert manifest["services"] == []
    assert manifest["plugins"] == []
    assert manifest["configuration"] == {"env": "test"}
    assert manifest["featureFlags"] == []
    assert manifest["contracts"] == list(KNOWN_CONTRACTS)
    assert manifest["providers"] == list(KNOWN_PROVIDERS)
    assert manifest["factories"] == list(KNOWN_FACTORIES)


def test_generate_manifest_reflects_live_capabilities() -> None:
    runtime = _running_runtime()
    runtime.register_capability(CapabilityBuilder(id="demo.cap", name="demo-cap").build())

    manifest = generate_manifest(runtime)

    assert len(manifest["capabilities"]) == 1  # type: ignore[arg-type]
    assert manifest["configuration"] == {}


def test_write_manifest_writes_valid_json_to_path(tmp_path: Path) -> None:
    runtime = _running_runtime()
    destination = tmp_path / "runtime.manifest.json"

    result_path = write_manifest(runtime, destination, configuration_summary={"env": "test"})

    assert result_path == destination
    assert destination.exists()
    content = json.loads(destination.read_text(encoding="utf-8"))
    assert content["framework"] == "TEAF"
    assert content["configuration"] == {"env": "test"}
