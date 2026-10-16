"""
routes/component3_routes.py
===========================

Component 3 API - registered on the EXISTING Component 2 FastAPI app
(see main.py). Adds:

    GET  /api/v1/component3/health
    POST /api/v1/component3/analyze
    GET  /api/v1/component3/model-card

Does not touch or import Component 2 request handling.
"""

from fastapi import APIRouter, HTTPException

from component3.pipeline import run_component3, health, Component3Error
from component3._models import get_model_card
from component3.schemas import (
    Component3Request,
    ClinicalReport,
    Component3Health,
)

router = APIRouter()


@router.get(
    "/component3/health",
    response_model=Component3Health,
    summary="Component 3 health & model status",
)
def component3_health():
    return health()


@router.get(
    "/component3/model-card",
    summary="Component 3 model card (data sources, metrics, disclaimers)",
)
def component3_model_card():
    card = get_model_card()
    if card is None:
        raise HTTPException(
            status_code=404,
            detail="model_card.json not found. Run: python -m Training.component3.train_all",
        )
    return card


@router.post(
    "/component3/analyze",
    response_model=ClinicalReport,
    summary="Multi-disorder classification, severity, confidence & unified risk",
)
def component3_analyze(request: Component3Request):
    try:
        return run_component3(
            session_id=request.session_id,
            user_id=request.user_id,
            component2_output=request.component2_output,
            temperature=request.temperature or 1.0,
        )
    except Component3Error as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500, detail=f"Component 3 pipeline error: {exc}"
        ) from exc
