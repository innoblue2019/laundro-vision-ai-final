from typing import Optional

from pydantic import BaseModel, Field


class CompetitorEvalRequest(BaseModel):
    q2_residential: int = Field(..., ge=1, le=5)
    q3_visibility: int = Field(..., ge=1, le=5)
    q4_signage: int = Field(..., ge=1, le=5)
    q5_motorcycle: int = Field(..., ge=1, le=5)
    q7_machine_status: int = Field(..., ge=1, le=5)
    q8_cleanliness: int = Field(..., ge=1, le=5)


class CompetitorEvalResponse(BaseModel):
    competitor_score: float
    knock_out: bool
    message: str


class AssessmentRequest(BaseModel):
    has_competitor: bool
    q1_cvs: int = Field(..., ge=1, le=5)
    q2_residential: int = Field(..., ge=1, le=5)
    q3_visibility: int = Field(..., ge=1, le=5)
    q4_signage: int = Field(..., ge=1, le=5)
    q5_motorcycle: int = Field(..., ge=1, le=5)
    q7_machine_status: Optional[int] = None
    q8_cleanliness: Optional[int] = None


class CategoryScores(BaseModel):
    audience: float
    hardware: float
    operations: Optional[float]


class AssessmentResponse(BaseModel):
    total_score: float
    category_scores: CategoryScores


class LocationEnrichRequest(BaseModel):
    address: str
    lat: float | None = None
    lng: float | None = None


class LocationEnrichResponse(BaseModel):
    has_competitor_in_1000m: bool
    competitors_data: list[str]
    cvs_mcd_in_200m: list[str]
    has_starbucks: bool
    recommended_q1_score: int
