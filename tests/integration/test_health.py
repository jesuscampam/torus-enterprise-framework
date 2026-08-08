"""Pruebas de integración de las rutas de sistema (backend/monitoring/health.py)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_instance_identity(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "TEAF"
    assert body["environment"] == "testing"


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "modules" in body


def test_live_returns_alive(client: TestClient) -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready_returns_ready(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "checks" in body


def test_response_includes_correlation_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert "x-correlation-id" in response.headers


def test_correlation_id_is_propagated_from_request_header(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-Id": "fixed-correlation-id"})
    assert response.headers["x-correlation-id"] == "fixed-correlation-id"
