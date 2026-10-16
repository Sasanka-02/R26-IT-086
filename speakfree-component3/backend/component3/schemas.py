"""
schemas.py
==========

Pydantic request / response models for the Component 3 API.

The request is intentionally permissive about the shape of `component2_output`
(it is a large, evolving structure owned by Component 2). Validation of the
actual feature content happens in `feature_adapter.adapt_features`, which
raises clear errors.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class Component3Request(BaseModel):
    session_id: Optional[str] = Field(
        default=None, description="Screening session id (preserved in the report)."
    )
    user_id: Optional[str] = Field(
        default=None, description="User id (preserved in the report)."
    )
    component2_output: dict[str, Any] = Field(
        ...,
        description=(
            "Component 2 output. Accepts the full C2 API response, the "
            "`component2_output` object, or the `component3_ready_output` "
            "handoff dict."
        ),
    )
    temperature: Optional[float] = Field(
        default=1.0,
        ge=0.05,
        le=10.0,
        description="Calibration temperature for confidence scaling (1.0 = off).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "sess-demo-001",
                "user_id": "demo-user",
                "component2_output": {
                    "component3_ready_output": {
                        "dysarthria_risk_score": 71.2,
                        "dysarthria_probability": 0.712,
                        "risk_level": "high",
                        "fluency_score": 58.0,
                        "word_repetition_count": 4,
                        "phrase_repetition_count": 1,
                        "filler_count": 3,
                        "speech_rate_wpm": 96.0,
                        "long_pause_count": 3,
                        "timing_consistency": None,
                        "duration_variation": None,
                        "phoneme_count": 0,
                        "alignment_reliability": None,
                        "alignment_uncertain": True,
                    }
                },
            }
        }
    }


# ---------------------------------------------------------------------------
# Response (documentation model - the pipeline returns a superset dict)
# ---------------------------------------------------------------------------

class UnifiedScore(BaseModel):
    severity_level: int
    severity_label: str
    risk_level: str
    confidence_score: float
    scoring_method: str
    scoring_explanation: list[str]


class UncertaintyBlock(BaseModel):
    confidence_score: float
    confidence_band: str
    normalised_entropy: float
    epistemic_std: float
    temperature: float
    method: str


class ClinicalReport(BaseModel):
    model_config = {"protected_namespaces": ()}

    session_id: str
    user_id: str
    primary_disorder: str
    severity_level: int
    severity_label: str
    risk_level: str
    confidence_score: float
    confidence_band: str

    disorder_breakdown: dict[str, float]
    severity_breakdown: dict[str, float]
    stuttering_events: dict[str, Optional[float]]
    stuttering_positive_events: list[str]
    articulation_metrics: dict[str, Any]

    uncertainty: UncertaintyBlock
    unified_score: UnifiedScore

    professional_review_recommended: bool
    recommendations: list[str]

    input_summary: dict[str, Any]
    model_status: dict[str, Any]
    model_version: str
    disclaimer: str
    processing_time_seconds: Optional[float] = None


class Component3Health(BaseModel):
    model_config = {"protected_namespaces": ()}

    component: str
    status: str
    models_trained: str
    models: dict[str, bool]
    model_version: str
    model_card_present: bool
    note: str
