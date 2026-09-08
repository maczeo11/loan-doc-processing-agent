"""
Smoke test for API health endpoint.
"""

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "finscan-api"
