from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "profile-service", "status": "ok"}
