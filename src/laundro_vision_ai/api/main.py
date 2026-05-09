import uvicorn
from fastapi import FastAPI, HTTPException

from laundro_vision_ai.models.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    CompetitorEvalRequest,
    CompetitorEvalResponse,
    LocationEnrichRequest,
    LocationEnrichResponse,
)
from laundro_vision_ai.services.location import calculate_q1_score, get_map_provider
from laundro_vision_ai.services.scoring import calculate_total_score, evaluate_competitor

app = FastAPI(title="LaundroVision AI MVP API")


@app.post("/api/v1/assessments/evaluate-competitor", response_model=CompetitorEvalResponse)
def evaluate_competitor_route(req: CompetitorEvalRequest):
    """Endpoint to evaluate competitor strength and determine knock‑out."""
    return evaluate_competitor(req)


@app.post("/api/v1/assessments/calculate-score", response_model=AssessmentResponse)
def calculate_score_route(req: AssessmentRequest):
    """Endpoint to calculate the total site score based on the questionnaire."""
    return calculate_total_score(req)


@app.post("/api/v1/locations/enrich", response_model=LocationEnrichResponse)
def enrich_location_route(req: LocationEnrichRequest):
    provider = get_map_provider()
    lat, lng = req.lat, req.lng

    if lat is None or lng is None:
        try:
            lat, lng = provider.geocode(req.address)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        data = provider.enrich_location(lat, lng)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"POI search failed: {str(e)}") from e

    q1_score = calculate_q1_score(data["has_starbucks"], data["cvs_mcd_in_200m"])

    return LocationEnrichResponse(
        has_competitor_in_1000m=data["has_competitor_in_1000m"],
        competitors_data=data["competitors_data"],
        cvs_mcd_in_200m=data["cvs_mcd_in_200m"],
        has_starbucks=data["has_starbucks"],
        recommended_q1_score=q1_score,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
