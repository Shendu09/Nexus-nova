"""Tests for server endpoints."""

import pytest
from fastapi.testclient import TestClient
from novaml.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_ping_endpoint(client):
    """Test /ping endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200


def test_health_endpoint(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_triage_no_auth(client):
    """Test /triage without auth."""
    response = client.post("/triage", json={"log_lines": ["test"]})
    assert response.status_code == 401


def test_triage_empty_logs(client):
    """Test /triage with empty logs."""
    response = client.post(
        "/triage",
        json={"log_lines": []},
        headers={"X-API-Key": "dev-key-change-in-prod"},
    )
    assert response.status_code == 400
