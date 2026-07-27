from app.main import app
from fastapi.testclient import TestClient


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "auth-service", "status": "hello world!"}


def test_metrics() -> None:
    client = TestClient(app)
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "nexus_app_info" in response.text
    assert "nexus_http_requests_total" in response.text
