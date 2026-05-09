import os

from fastapi.testclient import TestClient

from laundro_vision_ai.api.main import app

client = TestClient(app)


def test_evaluate_competitor_endpoint():
    response = client.post(
        "/api/v1/assessments/evaluate-competitor",
        json={
            "q2_residential": 4,
            "q3_visibility": 4,
            "q4_signage": 4,
            "q5_motorcycle": 4,
            "q7_machine_status": 4,
            "q8_cleanliness": 4,
        },
    )
    assert response.status_code == 200
    assert response.json()["knock_out"] is True


def test_calculate_score_endpoint():
    response = client.post(
        "/api/v1/assessments/calculate-score",
        json={
            "has_competitor": False,
            "q1_cvs": 5,
            "q2_residential": 5,
            "q3_visibility": 5,
            "q4_signage": 5,
            "q5_motorcycle": 5,
        },
    )
    assert response.status_code == 200
    assert response.json()["total_score"] == 5.0


def test_enrich_location_endpoint():
    os.environ["MAP_PROVIDER"] = "MOCK"
    from laundro_vision_ai.core.config import get_settings

    get_settings.cache_clear()

    response = client.post("/api/v1/locations/enrich", json={"address": "Taipei"})
    assert response.status_code == 200
    data = response.json()
    assert "has_competitor_in_1000m" in data
    assert "recommended_q1_score" in data
    assert data["recommended_q1_score"] in [1, 2, 3, 4, 5]

    if "MAP_PROVIDER" in os.environ:
        del os.environ["MAP_PROVIDER"]
    get_settings.cache_clear()
