import pytest
from pydantic import ValidationError

from laundro_vision_ai.models.schemas import (
    AssessmentRequest,
    CompetitorEvalRequest,
    LocationEnrichRequest,
    LocationEnrichResponse,
)


def test_competitor_eval_request_validation():
    req = CompetitorEvalRequest(
        q2_residential=4, q3_visibility=4, q4_signage=3, q5_motorcycle=5, q7_machine_status=4, q8_cleanliness=5
    )
    assert req.q2_residential == 4
    with pytest.raises(ValidationError):
        CompetitorEvalRequest(
            q2_residential=6, q3_visibility=4, q4_signage=3, q5_motorcycle=5, q7_machine_status=4, q8_cleanliness=5
        )


def test_assessment_request_validation():
    req = AssessmentRequest(
        has_competitor=False, q1_cvs=5, q2_residential=4, q3_visibility=3, q4_signage=4, q5_motorcycle=5
    )
    assert req.has_competitor is False


def test_location_enrich_request():
    req = LocationEnrichRequest(address="Taipei 101", lat=25.0, lng=121.5)
    assert req.address == "Taipei 101"


def test_location_enrich_response():
    resp = LocationEnrichResponse(
        has_competitor_in_1000m=True,
        competitors_data=["Laundry A"],
        cvs_mcd_in_200m=["7-11"],
        has_starbucks=False,
        recommended_q1_score=3,
    )
    assert resp.recommended_q1_score == 3
