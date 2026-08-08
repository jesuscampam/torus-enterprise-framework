"""Pruebas de integración de la Runtime API (backend/runtime/api.py, ``GET /runtime/*``)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_runtime_info_returns_diagnostics(client: TestClient) -> None:
    response = client.get("/runtime/info")
    assert response.status_code == 200
    body = response.json()
    assert body["frameworkVersion"] == "0.10.3-alpha"
    assert body["pythonVersion"]
    assert body["configurationSummary"]["environment"] == "testing"


def test_runtime_modules_lists_infrastructure_modules(client: TestClient) -> None:
    response = client.get("/runtime/modules")
    assert response.status_code == 200
    names = {module["name"] for module in response.json()}
    assert "database" in names
    assert "ai" in names


def test_runtime_services_returns_list(client: TestClient) -> None:
    response = client.get("/runtime/services")
    assert response.status_code == 200
    assert response.json() == []


def test_runtime_plugins_returns_list(client: TestClient) -> None:
    response = client.get("/runtime/plugins")
    assert response.status_code == 200
    assert response.json() == []


def test_runtime_capabilities_returns_list(client: TestClient) -> None:
    response = client.get("/runtime/capabilities")
    assert response.status_code == 200
    assert response.json() == []


def test_runtime_features_returns_list(client: TestClient) -> None:
    response = client.get("/runtime/features")
    assert response.status_code == 200
    assert response.json() == []


def test_runtime_events_includes_startup_events(client: TestClient) -> None:
    response = client.get("/runtime/events")
    assert response.status_code == 200
    names = {event["name"] for event in response.json()}
    assert "framework.started" in names
    assert "framework.startup.completed" in names


def test_runtime_events_limit_query_parameter(client: TestClient) -> None:
    response = client.get("/runtime/events", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_runtime_configuration_matches_testing_settings(client: TestClient) -> None:
    response = client.get("/runtime/configuration")
    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "testing"
    assert "appName" in body


def test_runtime_dependencies_returns_module_and_service_graphs(client: TestClient) -> None:
    response = client.get("/runtime/dependencies")
    assert response.status_code == 200
    body = response.json()
    assert "modules" in body
    assert body["services"] == []


def test_runtime_self_describes_the_framework(client: TestClient) -> None:
    response = client.get("/runtime/self")
    assert response.status_code == 200
    body = response.json()
    assert body["framework"] == "TEAF"
    assert body["version"] == "0.10.3-alpha"
    assert body["runtimeState"] == "running"
    assert body["supports"]["ai"] is True
