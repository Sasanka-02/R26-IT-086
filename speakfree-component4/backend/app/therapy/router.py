import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.therapy import audit, auth
from app.therapy.adaptive import (
    LEVELS,
    attempt_feedback,
    level_change_message,
    level_state,
    personal_target_wpm,
    score_attempt,
    verdict,
)
from app.therapy.assistant import answer, build_briefing
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.biomarker import compute_delta_vector, overall_progress_score
from app.therapy.dashboard import build_progress_summary
from app.therapy.exercises import EXERCISE_BANK, START_LEVEL, get_exercise, recommend_exercises, syllables_per_word
from app.therapy.federated_stub import get_federated_architecture
from app.therapy.privacy import budget_ledger
from app.therapy.progress_store import add_record, get_records, normalize_user_id
from app.therapy.realtime_feedback import process_metric, summarize
from app.therapy.schemas import (
    AssistantChatRequest,
    BiomarkerCompareRequest,
    DafCalibrationRequest,
    DafCalibrationResult,
    EndSessionRequest,
    ExerciseResultRequest,
    ExerciseType,
    LiveMetric,
    PrivacyBudgetResponse,
    ScreeningRequest,
    SessionSummary,
    SeverityLevel,
    StartSessionRequest,
    StartSessionResponse,
)
from app.therapy.session_store import end_session, get_session, start_session
from app.therapy.therapist_store import get_settings, set_screening

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
            quiet_warnings=0,
            syllables=0,
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


# --- Per-user exercises + results (adaptive learning) -------------------

@router.get("/exercises/user/{user_id}")
async def list_user_exercises(user_id: str, user: dict = Depends(auth.current_user)):
    """Full exercise bank for one student: reading levels above their level
    are locked, therapist-assigned exercises are flagged, and each passage's
    highlight speed is personalised to their past attempts."""
    auth.ensure_can_access(user, user_id)
    records = get_records(user_id)
    settings = get_settings(user_id)
    level = level_state(records, settings["level_override"])
    assigned = {a["exercise_id"] for a in settings["assigned"]}
    exercises = []
    for ex in EXERCISE_BANK:
        data = ex.model_dump(mode="json")
        data["locked"] = ex.level is not None and LEVELS.index(ex.level.value) > level["level_index"]
        data["assigned"] = ex.id in assigned
        if ex.target_wpm:
            data["base_wpm"] = ex.target_wpm
            data["target_wpm"] = personal_target_wpm(ex.target_wpm, ex.id, records)
        exercises.append(data)
    return {"level": level, "exercises": exercises}


def _measured_wpm(exercise, syllables: int | None, duration: float) -> int | None:
    if not syllables or not exercise.passage or duration < 5:
        return None
    words = syllables / syllables_per_word(exercise.passage)
    return int(round(words / (duration / 60)))


@router.post("/results")
async def submit_result(payload: ExerciseResultRequest, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, payload.user_id)
    exercise = get_exercise(payload.exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail="Unknown exercise")

    records = get_records(payload.user_id)
    settings = get_settings(payload.user_id)
    before = level_state(records, settings["level_override"])
    attempt = {
        "exercise_id": exercise.id,
        "exercise_type": exercise.type.value,
        "title": exercise.title,
        "level": exercise.level.value if exercise.level else None,
        "difficulty": exercise.difficulty,
        "duration_seconds": round(payload.duration_seconds, 1),
        "speaking_ratio": (
            round(payload.speaking_ratio, 3) if payload.speaking_ratio is not None else None
        ),
        "long_pauses": payload.long_pauses,
        "quiet_warnings": payload.quiet_warnings,
        "syllables": payload.syllables,
        "measured_wpm": _measured_wpm(exercise, payload.syllables, payload.duration_seconds),
        "target_wpm": payload.target_wpm or exercise.target_wpm,
        "self_rating": payload.self_rating.value,
        "disfluencies": payload.disfluencies,
    }
    score, breakdown = score_attempt(attempt)
    stored = add_record(payload.user_id, {**attempt, "score": score, "score_breakdown": breakdown})
    after = level_state(records + [stored], settings["level_override"])
    return {
        "record": stored,
        "score": score,
        "verdict": verdict(score),
        "feedback": attempt_feedback(stored),
        "breakdown": breakdown,
        "measured_wpm": stored["measured_wpm"],
        "target_wpm": stored["target_wpm"],
        "level": after,
        "level_message": level_change_message(before, after),
    }


# --- SO3: Dashboard + adaptive weekly plan ------------------------------

@router.get("/progress/{user_id}")
async def get_progress(user_id: str, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, user_id)
    return build_progress_summary(normalize_user_id(user_id), get_records(user_id))


@router.get("/plan/{user_id}")
async def get_weekly_plan(user_id: str, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, user_id)
    plan = recommend_weekly_plan(get_records(user_id), get_settings(user_id))
    return {"user_id": normalize_user_id(user_id), **plan}


# --- Integration with Components 1–3: screening result -------------------

@router.post("/screening")
async def submit_screening(payload: ScreeningRequest, user: dict = Depends(auth.current_user)):
    """Receives the stuttering severity from the screening components. It sets
    the starting reading level (severe/moderate -> Beginner, mild ->
    Intermediate) while the student has no reading attempts, and steers the
    weekly plan towards exercises recommended for that severity."""
    auth.ensure_can_access(user, payload.user_id)
    records = get_records(payload.user_id)
    has_reading = any(r["exercise_type"] == "reading" for r in records)
    start = START_LEVEL.get(payload.severity) if not has_reading else None
    settings = set_screening(payload.user_id, payload.severity.value, payload.source, user["email"], start)
    audit.log(user["email"], "screening.received", normalize_user_id(payload.user_id),
              severity=payload.severity.value, source=payload.source, starting_level=start)
    return {
        "screening": settings["screening"],
        "starting_level_applied": start,
        "level": level_state(records, settings["level_override"]),
        "plan": recommend_weekly_plan(records, settings),
    }


# --- Therapy Assistant ---------------------------------------------------

@router.get("/assistant/{user_id}")
async def get_assistant_briefing(user_id: str, name: str = "", user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, user_id)
    return build_briefing(normalize_user_id(user_id), name, get_records(user_id))


@router.post("/assistant/chat")
async def assistant_chat(payload: AssistantChatRequest, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, payload.user_id)
    return answer(
        normalize_user_id(payload.user_id),
        payload.name,
        payload.message,
        get_records(payload.user_id),
    )


# --- SO5: Privacy budget -------------------------------------------------

@router.get("/privacy/budget/{session_id}", response_model=PrivacyBudgetResponse)
async def get_privacy_budget(session_id: str, user: dict = Depends(auth.current_user)):
    """Budget spent on differentially private cohort releases (shared by the clinic)."""
    return PrivacyBudgetResponse(**budget_ledger.status("cohort-report"))


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
