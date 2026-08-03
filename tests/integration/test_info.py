"""Pruebas de integración de la ruta /info (backend/monitoring/info.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient

_EXPECTED_MODULES = {
    "database",
    "security",
    "telemetry",
    "storage",
    "ai",
    "scheduler",
    "notification",
}


def test_info_returns_version_and_environment(client: TestClient) -> None:
    response = client.get("/info")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.4.0-alpha"
    assert body["environment"] == "testing"


def test_info_lists_all_infrastructure_modules_as_contracts_only(client: TestClient) -> None:
    response = client.get("/info")
    body = response.json()

    module_names = {module["name"] for module in body["modules"]}
    assert module_names == _EXPECTED_MODULES
    assert all(module["status"] == "contracts_only" for module in body["modules"])


def test_info_includes_runtime_state(client: TestClient) -> None:
    response = client.get("/info")
    body = response.json()

    assert body["state"] == "running"
    assert body["lifecycleStage"] == "running"
    assert set(body["loadedModules"]) == _EXPECTED_MODULES
    assert body["registeredCapabilities"] == []
