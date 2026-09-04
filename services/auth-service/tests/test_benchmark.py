from app.api.routes.benchmark import arm, clear
from app.core.config import settings
from app.main import app
from app.metrics import render_metrics
from fastapi.testclient import TestClient


def test_benchmark_fault_metric_can_be_armed_and_cleared() -> None:
    arm("A01", "run-1", "HTTP errors observed")
    assert (
        'scenario="A01",run_id="run-1",symptom="HTTP errors observed"} 1'
        in render_metrics("auth", "test")
    )

    clear("A01", "run-1")
    assert 'scenario="A01",run_id="run-1",symptom="cleared"} 0' in render_metrics(
        "auth", "test"
    )


def test_benchmark_routes_are_disabled_by_default() -> None:
    assert settings.AIOPS_BENCHMARK_ENABLED is False
    response = TestClient(app).post(
        "/_benchmark/arm",
        params={"scenario": "A01", "run_id": "test", "symptom": "test"},
    )
    assert response.status_code == 404
