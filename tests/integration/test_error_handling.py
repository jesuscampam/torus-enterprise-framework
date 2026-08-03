"""Pruebas de integración del manejo centralizado de errores
(backend/middleware/exception_handler.py) — formato RFC 7807 end-to-end."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_route_not_found_returns_rfc7807_format(client: TestClient) -> None:
    response = client.get("/no-existe")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == 404
    assert body["type"].startswith("https://teaf.torus/errors/")
    assert body["instance"] == "/no-existe"
    assert "correlationId" in body


def test_method_not_allowed_returns_rfc7807_format(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 405
    body = response.json()
    assert body["status"] == 405
    assert "correlationId" in body
