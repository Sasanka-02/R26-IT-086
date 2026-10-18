"""
Integration API.

Admin only (technical, C2/C3 internals):
  GET  /api/v1/admin/pipeline                    overview: every pipeline run + KPIs
  GET  /api/v1/admin/pipeline/{session_id}       one run: C1 summary, C2 report, C3 report, C4 profile
  POST /api/v1/admin/pipeline/{session_id}/rerun re-run C2 -> C3 -> C4 for a session
  GET  /api/v1/admin/models                      C3 model card + health, C2 formulas, C4 engine settings
  GET  /api/v1/admin/patients/{id}/therapy       C4 monitor: profile history, plan engine, attempts, chat log

Therapist (admin, or the clinician who owns the patient):
  PATCH /api/v1/admin/patients/{id}/therapy-settings   pin the practice bracket (1-8) / assign exercises

Patient / guardian / clinician (own patients only, patient-safe - no disorder or severity):
  GET  /api/v1/therapy/{patient_id}/plan                 adaptive plan (today, week, goals, progress)
  POST /api/v1/therapy/{patient_id}/attempts             save an exercise result -> score + level change
  GET  /api/v1/therapy/{patient_id}/assistant            assistant briefing
  POST /api/v1/therapy/{patient_id}/assistant/chat       ask the assistant
  WS   /ws/therapy-live/{live_id}?token=                 live coaching (on-device metrics only)
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from age_brackets import bracket_for_age, bracket_info, patient_age
from auth import decode_token, get_current_user, get_owned_patient, require_admin
from database import (
    AssistantMessage,
    Patient,
    PipelineRun,
    ScreeningSession,
    SessionLocal,
    TherapyAttempt,
    TherapyGoal,
    TherapyHomework,
    TherapyProfile,
    User,
    as_utc,
    get_db,
    utcnow,
)

from . import COMPONENT_DIRS  # noqa: F401  (sys.path bootstrap)
from .pipeline import run_session_pipeline

log = logging.getLogger("speakfree.integration")
router = APIRouter()

PATIENT_PLAN_KEYS = ("learner", "focus", "dose", "level", "skill_level", "word_level", "today", "week", "goals",
                     "homework", "rescreen", "progress", "dashboard", "why", "library")


# ============================================================================= helpers
def _iso(dt: datetime | None) -> str | None:
    return as_utc(dt).isoformat(timespec="seconds") if dt else None


def _records(db: Session, patient_id: str) -> list[dict]:
    rows = db.scalars(select(TherapyAttempt).where(TherapyAttempt.patient_id == patient_id)
                      .order_by(TherapyAttempt.completed_at, TherapyAttempt.id)).all()
    return [{**json.loads(r.record_json), "attempt_id": r.id} for r in rows]


def _active_profile(db: Session, patient_id: str) -> dict | None:
    row = db.scalar(select(TherapyProfile).where(TherapyProfile.patient_id == patient_id)
                    .order_by(TherapyProfile.created_at.desc(), TherapyProfile.id.desc()).limit(1))
    return json.loads(row.profile_json) if row else None


def _require_profile(db: Session, patient_id: str) -> dict:
    profile = _active_profile(db, patient_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No therapy plan yet - complete a screening first.")
    return profile


def _learner(db: Session, patient: Patient) -> dict:
    """What C4 needs to know about the person practising: age bracket + the therapist's settings."""
    age = patient_age(patient)
    assigned = list(patient.assigned_exercises or [])
    hw = {h.exercise_id: h for h in db.scalars(select(TherapyHomework).where(TherapyHomework.patient_id == patient.id))}
    goals = db.scalars(select(TherapyGoal).where(TherapyGoal.patient_id == patient.id).order_by(TherapyGoal.id)).all()
    return {
        "age": age,
        "age_bracket": bracket_for_age(age),
        "bracket_override": patient.age_bracket_override,
        "assigned": assigned,
        "homework": [{"exercise_id": ex_id,
                      "assigned_at": _iso(hw[ex_id].assigned_at) if ex_id in hw else None,
                      "due": hw[ex_id].due.isoformat() if ex_id in hw and hw[ex_id].due else None,
                      "times": hw[ex_id].times if ex_id in hw else 1} for ex_id in assigned],
        "goals": [{"id": g.id, "metric": g.metric, "target": g.target} for g in goals],
        "daf_delay_ms": patient.daf_delay_ms,
    }


def _patient_summary(patient: Patient) -> dict:
    age = patient_age(patient)
    b = bracket_for_age(age)
    return {"id": patient.id, "full_name": patient.full_name, "age": age,
            "age_bracket": bracket_info(b) if b else None,
            "age_bracket_override": patient.age_bracket_override,
            "assigned_exercises": list(patient.assigned_exercises or [])}


def _plan(db: Session, profile: dict, records: list[dict], patient: Patient) -> dict:
    from component4 import build_plan

    return build_plan(profile, records, learner=_learner(db, patient))


def _patient_plan(plan: dict) -> dict:
    """Patient view: the plan without the engine internals (and no disorder / severity anywhere)."""
    return {"has_profile": True, **{k: plan[k] for k in PATIENT_PLAN_KEYS}}


# ============================================================================= admin
@router.get("/api/v1/admin/pipeline", tags=["admin: pipeline"])
def admin_pipeline(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    runs = db.scalars(select(PipelineRun).order_by(PipelineRun.created_at.desc())).all()
    sessions = {s.id: s for s in db.scalars(select(ScreeningSession).where(
        ScreeningSession.id.in_([r.session_id for r in runs]))).all()} if runs else {}
    rows = []
    for r in runs:
        s = sessions.get(r.session_id)
        indicator = json.loads(s.summary_json)["screening_indicator"] if s else {}
        rows.append({
            "session_id": r.session_id, "patient_id": r.patient_id, "patient_name": r.patient.full_name,
            "created_at": _iso(r.created_at), "status": r.status, "error": r.error,
            "c1_overall_score": s.overall_speech_score if s else None, "c1_severity_hint": indicator.get("severity_hint"),
            "articulation_score": r.articulation_score, "primary_disorder": r.primary_disorder,
            "severity_level": r.severity_level, "risk_level": r.risk_level, "therapy_focus": r.therapy_focus,
        })
    done = [r for r in runs if r.status == "completed"]
    week_ago = utcnow() - timedelta(days=7)
    attempts_total = db.scalar(select(func.count()).select_from(TherapyAttempt)) or 0
    active = db.scalar(select(func.count(func.distinct(TherapyAttempt.patient_id)))
                       .where(TherapyAttempt.completed_at >= week_ago)) or 0
    scores = [r.articulation_score for r in runs if r.articulation_score is not None]
    return {
        "kpis": {
            "sessions": len(runs),
            "completed": len(done),
            "failed": sum(1 for r in runs if r.status != "completed"),
            "average_articulation": round(sum(scores) / len(scores), 1) if scores else None,
            "disorders": dict(Counter(r.primary_disorder for r in done)),
            "severity": dict(Counter(str(r.severity_level) for r in done)),
            "risk": dict(Counter(r.risk_level for r in done)),
            "therapy_attempts": attempts_total,
            "active_patients_7d": active,
        },
        "runs": rows,
    }


@router.get("/api/v1/admin/pipeline/{session_id}", tags=["admin: pipeline"])
def admin_pipeline_run(session_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    run = db.get(PipelineRun, session_id)
    session = db.get(ScreeningSession, session_id)
    if run is None or session is None:
        raise HTTPException(status_code=404, detail="No pipeline run for this session")
    profile_row = db.scalar(select(TherapyProfile).where(TherapyProfile.session_id == session_id))
    p = run.patient
    return {
        "session_id": session_id, "status": run.status, "error": run.error, "created_at": _iso(run.created_at),
        "patient": {"id": p.id, "full_name": p.full_name, "age": patient_age(p)},
        "stage_timings": json.loads(run.stage_timings_json or "{}"),
        "c1_summary": json.loads(session.summary_json),
        "c2": json.loads(run.c2_json) if run.c2_json else None,
        "c3": json.loads(run.c3_json) if run.c3_json else None,
        "c4_profile": json.loads(profile_row.profile_json) if profile_row else None,
    }


@router.post("/api/v1/admin/pipeline/{session_id}/rerun", tags=["admin: pipeline"])
async def admin_pipeline_rerun(session_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(ScreeningSession, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    run = await run_in_threadpool(run_session_pipeline, db, session_id)
    return {"session_id": session_id, "status": run.status, "error": run.error}


@router.get("/api/v1/admin/models", tags=["admin: pipeline"])
def admin_models(_: User = Depends(require_admin)):
    from component2.articulation_score import CLEAR_WORD_WEIGHT, CONFIDENCE_WEIGHT, FILLERS, LEVEL_BANDS
    from component3 import health
    from component3._models import get_model_card
    from component4 import bandit, brackets, categories, scoring
    from component4.intent_classifier import leave_one_out_accuracy

    return {
        "component2": {
            "equations": [
                {"id": "C2-Eq.1", "name": "Word accuracy (reading)", "formula": "WA = 100 × max(0, 1 − (S + D + I) / N)"},
                {"id": "C2-Eq.2", "name": "Kept-token confidence", "formula": "C = (1/M) × Σ P(t_j)  over non-filler tokens"},
                {"id": "C2-Eq.3", "name": "Clear-word ratio", "formula": "CWR = (N − L) / N"},
                {"id": "C2-Eq.4", "name": "Articulation score", "formula": f"A = 100 × ({CONFIDENCE_WEIGHT} × C + {CLEAR_WORD_WEIGHT} × CWR)"},
                {"id": "C2-Eq.5", "name": "Session articulation", "formula": "A_session = Σ N_r·A_r / Σ N_r"},
            ],
            "fillers": sorted(FILLERS),
            "level_bands": [{"min": lo, "label": label} for lo, label in LEVEL_BANDS],
        },
        "component3": {"health": health(), "model_card": get_model_card()},
        "component4": {
            "scoring_weights": scoring.WEIGHTS,
            "thresholds": scoring.THRESHOLDS,
            "bandit": {"alpha": bandit.ALPHA, "category_beta": bandit.CATEGORY_BETA,
                       "difficulty_penalty": bandit.DIFFICULTY_PENALTY, "context_dim": bandit.CONTEXT_DIM},
            "dose_by_severity": categories.DOSE_BY_SEVERITY,
            "start_level_by_severity": categories.START_LEVEL_BY_SEVERITY,
            "age_brackets": brackets.BRACKETS,
            "foci": {k: {"admin_name": v["admin_name"], "patient_name": v["patient_name"],
                         "ladder_type": v["ladder_type"], "c3_disorder": v["c3_disorder"]}
                     for k, v in categories.FOCI.items()},
            "intent_classifier": leave_one_out_accuracy(),
        },
    }


@router.get("/api/v1/admin/patients/{patient_id}/therapy", tags=["admin: pipeline"])
def admin_patient_therapy(patient_id: str, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    profiles = db.scalars(select(TherapyProfile).where(TherapyProfile.patient_id == patient_id)
                          .order_by(TherapyProfile.created_at.desc())).all()
    records = _records(db, patient_id)
    profile = json.loads(profiles[0].profile_json) if profiles else None
    chats = db.scalars(select(AssistantMessage).where(AssistantMessage.patient_id == patient_id)
                       .order_by(AssistantMessage.created_at.desc()).limit(50)).all()
    from .therapist_routes import rated_records, therapist_panel

    plan = _plan(db, profile, records, patient) if profile else None
    return {
        "patient": _patient_summary(patient),
        "profile": profile,
        "profile_history": [
            {"session_id": p.session_id, "focus": p.focus, "severity_level": p.severity_level, "created_at": _iso(p.created_at)}
            for p in profiles
        ],
        "plan": plan,
        "attempts": list(reversed(rated_records(db, records, user))),
        "therapist": therapist_panel(db, patient, records, plan),
        "assistant_log": [
            {"question": c.question, "reply": c.reply, "intent": c.intent, "confidence": c.confidence,
             "source": c.source, "created_at": _iso(c.created_at)} for c in chats
        ],
    }


class TherapySettings(BaseModel):
    age_bracket_override: int | None = Field(default=None, ge=1, le=8)   # null -> follow the adaptive ladder
    assigned_exercise_ids: list[str] | None = Field(default=None, max_length=10)


@router.patch("/api/v1/admin/patients/{patient_id}/therapy-settings", tags=["admin: pipeline"])
def therapist_settings(patient_id: str, body: TherapySettings, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """A therapist pins the practice bracket and/or assigns exercises. Only fields sent are changed."""
    from component4.exercises import get_exercise

    if user.role == "admin":
        patient = db.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
    elif user.role == "clinician":
        patient = get_owned_patient(db, user, patient_id)
    else:
        raise HTTPException(status_code=403, detail="Only a therapist can change the practice level")
    if "age_bracket_override" in body.model_fields_set:
        patient.age_bracket_override = body.age_bracket_override
    if "assigned_exercise_ids" in body.model_fields_set:
        ids = list(dict.fromkeys(body.assigned_exercise_ids or []))
        unknown = [i for i in ids if get_exercise(i) is None]
        if unknown:
            raise HTTPException(status_code=422, detail=f"Unknown exercise(s): {', '.join(unknown)}")
        patient.assigned_exercises = ids or None
        # homework rows follow the assignment: new ones start now (1 attempt, no due date), removed ones go
        existing = {h.exercise_id: h for h in db.scalars(select(TherapyHomework).where(TherapyHomework.patient_id == patient.id))}
        for ex_id, row in existing.items():
            if ex_id not in ids:
                db.delete(row)
        for ex_id in ids:
            if ex_id not in existing:
                db.add(TherapyHomework(patient_id=patient.id, exercise_id=ex_id, times=1, assigned_by_user_id=user.id))
    db.commit()
    return _patient_summary(patient)


# ============================================================================= patient therapy
@router.get("/api/v1/therapy/{patient_id}/plan", tags=["therapy"])
def therapy_plan(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    profile = _active_profile(db, patient.id)
    if profile is None:
        return {"has_profile": False}
    return _patient_plan(_plan(db, profile, _records(db, patient.id), patient))


@router.post("/api/v1/therapy/{patient_id}/attempts", tags=["therapy"])
def therapy_attempt(patient_id: str, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4 import attempt_result, build_attempt
    from component4.schemas import AttemptRequest
    from component4.session_store import end_session
    from component4.realtime_feedback import summarize

    patient = get_owned_patient(db, user, patient_id)
    profile = _require_profile(db, patient.id)
    try:
        payload = AttemptRequest.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    live = None
    if payload.live_session_id:
        state = end_session(payload.live_session_id)
        live = summarize(state) if state else None
    records = _records(db, patient.id)
    try:
        stored = build_attempt(profile, payload.model_dump(), live)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown exercise") from exc
    row = TherapyAttempt(patient_id=patient.id, exercise_id=stored["exercise_id"], exercise_type=stored["exercise_type"],
                         score=stored["score"], record_json=json.dumps(stored),
                         completed_at=datetime.fromisoformat(stored["completed_at"]))
    db.add(row)
    db.commit()
    stored = {**stored, "attempt_id": row.id}
    plan_before = _plan(db, profile, records, patient)
    result = attempt_result(profile, records, stored, _learner(db, patient))
    plan = _plan(db, profile, records + [stored], patient)
    before = {b["id"] for b in plan_before["dashboard"]["badges"] if b["earned"]}
    new_badges = [b for b in plan["dashboard"]["badges"] if b["earned"] and b["id"] not in before]
    return {**result, "new_badges": new_badges, "plan": _patient_plan(plan)}


@router.get("/api/v1/therapy/{patient_id}/assistant", tags=["therapy"])
def therapy_assistant(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4 import build_briefing

    patient = get_owned_patient(db, user, patient_id)
    profile = _require_profile(db, patient.id)
    return build_briefing(patient.full_name, profile, _plan(db, profile, _records(db, patient.id), patient))


@router.post("/api/v1/therapy/{patient_id}/assistant/chat", tags=["therapy"])
async def therapy_chat(patient_id: str, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4 import answer
    from component4.schemas import ChatRequest

    patient = get_owned_patient(db, user, patient_id)
    profile = _require_profile(db, patient.id)
    try:
        req = ChatRequest.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Message must be 1-500 characters") from exc
    records = _records(db, patient.id)
    plan = _plan(db, profile, records, patient)
    reply = await run_in_threadpool(answer, req.message, patient.full_name, profile, plan, records)
    db.add(AssistantMessage(patient_id=patient.id, question=req.message[:500], reply=reply["reply"],
                            intent=reply.get("intent"), confidence=float(reply.get("confidence") or 0), source=reply["source"]))
    db.commit()
    return reply


# ============================================================================= live coaching (C4 SO1)
@router.websocket("/ws/therapy-live/{live_id}")
async def therapy_live(ws: WebSocket, live_id: str, token: str | None = Query(None), exercise_type: str | None = Query(None)):
    """Browser sends on-device metrics every 500 ms (never audio); server replies with coaching."""
    from component4.realtime_feedback import process_metric
    from component4.schemas import LiveMetric
    from component4.session_store import start_session

    user_id = decode_token(token) if token else None
    with SessionLocal() as db:
        ok = user_id is not None and db.get(User, user_id) is not None
    if not ok:
        await ws.close(code=1008)
        return
    await ws.accept()
    state = start_session(live_id, exercise_type)
    try:
        while True:
            metric = LiveMetric(**(await ws.receive_json()))
            feedback = process_metric(state, metric)
            if feedback is not None:
                await ws.send_json(feedback.model_dump())
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        log.exception("Live therapy socket error")
        await ws.close()
