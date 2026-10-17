from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping():
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["message"] == "pong"


def test_mobile_app():
    response = client.get("/mobile")
    assert response.status_code == 200
    assert "NaSCon 26" in response.text
