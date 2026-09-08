from fastapi.testclient import TestClient

from service.main import app


def test_surrogate_comparison_api_exposes_live_model_review():
    response = TestClient(app).get("/surrogate-comparison?n_samples=40&seed=3")
    assert response.status_code == 200
    body = response.json()
    assert body["n_samples"] == 40
    assert len(body["comparison"]) == 4
    assert {row["selected_for_exploration"] for row in body["comparison"]} <= {"gaussian_process", "random_forest"}
    assert "physics outputs" in body["claim_boundary"]
