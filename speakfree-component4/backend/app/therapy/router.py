import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.therapy.bandit import build_context, recommend_weekly_plan, record_week_outcome
from app.therapy.biomarker import compute_delta_vector, overall_progress_score
from app.therapy.dashboard import generate_weekly_trend, summarize_streak
from app.therapy.exercises import recommend_exercises
from app.therapy.federated_stub import get_federated_architecture
from app.therapy.privacy import budget_ledger, privatize_statistic
from app.therapy.realtime_feedback import process_metric, summarize
from app.therapy.schemas import (
    BiomarkerCompareRequest,
    DafCalibrationRequest,
    DafCalibrationResult,
    EndSessionRequest,
    ExerciseType,
    LiveMetric,
    PrivacyBudgetResponse,
    SessionSummary,
    SeverityLevel,
    StartSessionRequest,
    StartSessionResponse,
    WeeklyPlanRequest,
    WeeklyPlanResponse,
)
from app.therapy.session_store import end_session, get_session, start_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/therapy", tags=["therapy"])


# --- SO1: Real-time coach ---------------------------------------------

@router.get("/exercises", response_model=list)
async def list_exercises(severity: SeverityLevel = SeverityLevel.UNKNOWN):
    return recommend_exercises(severity)


@router.post("/session/start", response_model=StartSessionResponse)
async def start_therapy_session(payload: StartSessionRequest):
    start_session(payload.session_id)
    exercises = recommend_exercises(payload.severity)
    return StartSessionResponse(
        session_id=payload.session_id, recommended_exercises=exercises
    )


@router.post("/session/end", response_model=SessionSummary)
async def end_therapy_session(payload: EndSessionRequest):
    state = end_session(payload.session_id)
    if state is None:
        return SessionSummary(
            session_id=payload.session_id,
            duration_seconds=0,
            exercise_type=None,
            speaking_ratio=0,
            avg_energy=0,
            pause_count=0,
            feedback_events=0,
        )
    stats = summarize(state)
    return SessionSummary(session_id=payload.session_id, **stats)


@router.websocket("/ws/{session_id}")
async def therapy_feedback_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    state = get_session(session_id)
    if state is None:
        state = start_session(session_id)

    exercise_type = websocket.query_params.get("exercise_type")
    if exercise_type in (ExerciseType.PACING.value, ExerciseType.DAF.value):
        state.exercise_type = ExerciseType(exercise_type)

    try:
        while True:
            raw = await websocket.receive_json()
            metric = LiveMetric(**raw)
            feedback = process_metric(state, metric)
            if feedback is not None:
                await websocket.send_json(feedback.model_dump())
    except WebSocketDisconnect:
        logger.info("Therapy WS disconnected for session %s", session_id)
    except Exception:
        logger.exception("Therapy WS error for session %s", session_id)
        await websocket.close()


# --- SO2: DAF calibration ----------------------------------------------

@router.post("/daf/calibrate", response_model=DafCalibrationResult)
async def calibrate_daf(payload: DafCalibrationRequest):
    """
    Picks the delay that minimises (stutter_events * deviation_from_target_rate),
    per the proposal's calibration protocol.
    """
    target_rate = 130.0
    best_trial = min(
        payload.trials,
        key=lambda t: t.stutter_events * abs(t.speech_rate_wpm - target_rate),
    )
    return DafCalibrationResult(
        session_id=payload.session_id,
        recommended_delay_ms=best_trial.delay_ms,
        trials_evaluated=len(payload.trials),
    )


# --- SO3: Dashboard + adaptive weekly plan ------------------------------

@router.get("/dashboard/{session_id}")
async def get_dashboard(session_id: str):
    trend = generate_weekly_trend()
    streak = summarize_streak(trend)
    for week in trend:
        week["stuttering_events_per_min"] = round(
            privatize_statistic(week["stuttering_events_per_min"], sensitivity=0.5, epsilon=3.0),
            2,
        )
    return {"session_id": session_id, "weekly_trend": trend, **streak}


@router.post("/plan/weekly", response_model=WeeklyPlanResponse)
async def get_weekly_plan(payload: WeeklyPlanRequest):
    context = build_context(
        payload.severity_level, payload.avg_stutter_freq, payload.trend, payload.comfort_score
    )
    exercises = recommend_weekly_plan(context)

    budget_ledger.spend(payload.session_id, epsilon=0.1)

    return WeeklyPlanResponse(session_id=payload.session_id, exercises=exercises)


# --- SO5: Privacy budget -------------------------------------------------

@router.get("/privacy/budget/{session_id}", response_model=PrivacyBudgetResponse)
async def get_privacy_budget(session_id: str):
    return PrivacyBudgetResponse(**budget_ledger.status(session_id))


# --- SO4: Federated learning architecture (design stub, not live) --------

@router.get("/federated/architecture")
async def federated_architecture():
    return get_federated_architecture()


# --- Sixth capability: biomarker comparison -------------------------------

@router.post("/biomarker/compare")
async def compare_biomarker(payload: BiomarkerCompareRequest):
    delta = compute_delta_vector(payload.task_type, payload.patient_metrics)
    score = overall_progress_score(delta)
    return {"delta_vector": delta, "progress_score": score}
