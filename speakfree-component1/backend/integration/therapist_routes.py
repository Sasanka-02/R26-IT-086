"""
Therapist controls, patient notes, DAF calibration, privacy, usability survey and evidence (Component 4).

Therapist (admin, or the clinician who owns the patient):
  POST   /api/v1/admin/patients/{id}/goals                 add a measurable goal
  DELETE /api/v1/admin/patients/{id}/goals/{goal_id}       remove it
  POST   /api/v1/admin/patients/{id}/notes                 clinical note (shared with the patient or private)
  PATCH  /api/v1/admin/patients/{id}/homework/{exercise}   due date + attempts asked for (assigned exercise)
  PUT    /api/v1/admin/attempts/{attempt_id}/rating        rate an attempt 1-5 (expert validation)
  POST   /api/v1/admin/patients/{id}/plan-review           judge the generated plan

Patient / guardian (own patients only):
  GET  /api/v1/therapy/{id}/notes           shared notes, new ones marked unread
  POST /api/v1/therapy/{id}/notes/read      mark them read
  POST /api/v1/therapy/{id}/daf/calibrate   5 delay trials -> recommended delay (saved)
  GET  /api/v1/therapy/{id}/privacy         what is stored, what never is, the clinic's ε budget
  GET  /api/v1/therapy/{id}/export          download the patient's own therapy data (JSON)

Any account:
  GET  /api/v1/survey      System Usability Scale items + whether to invite this account
  POST /api/v1/survey      submit (one response per account; a repeat replaces it)

Admin:
  GET /api/v1/admin/evidence                expert agreement, recalibration, inter-rater, plan reviews, SUS, privacy
  GET /api/v1/admin/evidence/cohort?epsilon differentially private cohort report (spends ε once per data snapshot)
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import get_current_user, get_owned_patient, require_admin
from database import (
    AssistantMessage,
    AttemptRating,
    Patient,
    PlanReview,
    PrivacyLedgerEntry,
    ScreeningSession,
    TherapyAttempt,
    TherapyGoal,
    TherapyHomework,
    TherapyNote,
    TherapyProfile,
    UsabilitySurvey,
    User,
    as_utc,
    get_db,
    utcnow,
)

from .routes import _active_profile, _iso, _learner, _plan, _records, _require_profile

router = APIRouter()
COHORT_LEDGER = "cohort-report"


def therapist_patient(db: Session, user: User, patient_id: str) -> Patient:
    """Admin: any patient. Clinician: own patients. Everyone else: 403."""
    if user.role == "admin":
        patient = db.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient
    if user.role == "clinician":
        return get_owned_patient(db, user, patient_id)
    raise HTTPException(status_code=403, detail="Only a therapist can do this")


# ============================================================================= admin therapy view helpers
def rated_records(db: Session, records: list[dict], viewer: User) -> list[dict]:
    """Attempt records with every therapist rating (and the viewer's own)."""
    ids = [r["attempt_id"] for r in records if r.get("attempt_id")]
    rows = db.scalars(select(AttemptRating).where(AttemptRating.attempt_id.in_(ids))).all() if ids else []
    by_attempt: dict[int, list[AttemptRating]] = {}
    for row in rows:
        by_attempt.setdefault(row.attempt_id, []).append(row)
    out = []
    for r in records:
        ratings = by_attempt.get(r.get("attempt_id"), [])
        mine = next((x for x in ratings if x.rater_user_id == viewer.id), None)
        out.append({**r,
                    "ratings": [{"rating": x.rating, "note": x.note, "rater": x.rater.full_name,
                                 "mine": x.rater_user_id == viewer.id, "created_at": _iso(x.created_at)} for x in ratings],
                    "my_rating": mine.rating if mine else None})
    return out


def _note_out(n: TherapyNote, read_at=None) -> dict:
    at = as_utc(n.created_at)
    return {"id": n.id, "text": n.text, "by_name": n.author_name, "shared": n.shared, "at": _iso(n.created_at),
            "unread": read_at is None or at > as_utc(read_at)}


def therapist_panel(db: Session, patient: Patient, records: list[dict], plan: dict | None) -> dict:
    from component4.evaluation import PLAN_VERDICTS
    from component4.exercises import exercises_for
    from component4.therapist import GOAL_METRICS, alerts, goal_progress, homework_status

    learner = _learner(db, patient)
    goals = db.scalars(select(TherapyGoal).where(TherapyGoal.patient_id == patient.id).order_by(TherapyGoal.id)).all()
    notes = db.scalars(select(TherapyNote).where(TherapyNote.patient_id == patient.id)
                       .order_by(TherapyNote.created_at.desc(), TherapyNote.id.desc())).all()
    reviews = db.scalars(select(PlanReview).where(PlanReview.patient_id == patient.id)
                         .order_by(PlanReview.created_at.desc()).limit(5)).all()
    homework = (plan["homework"]["items"] if plan else
                homework_status(learner["homework"], records, titles={e["id"]: e for e in exercises_for(None)}))
    unrated = sum(1 for r in records if r.get("attempt_id")) - (db.scalar(
        select(func.count(func.distinct(AttemptRating.attempt_id))).select_from(AttemptRating)
        .join(TherapyAttempt, AttemptRating.attempt_id == TherapyAttempt.id)
        .where(TherapyAttempt.patient_id == patient.id)) or 0)
    return {
        "goal_metrics": [{"metric": k, **v} for k, v in GOAL_METRICS.items()],
        "goals": goal_progress(learner["goals"], records),
        "goal_rows": [{"id": g.id, "metric": g.metric, "target": g.target, "created_at": _iso(g.created_at)} for g in goals],
        "notes": [_note_out(n, patient.notes_read_at) for n in notes],
        "homework": homework,
        "plan_reviews": [{"id": r.id, "verdict": r.verdict, "label": PLAN_VERDICTS.get(r.verdict, r.verdict),
                          "note": r.note, "at": _iso(r.created_at)} for r in reviews],
        "plan_verdicts": PLAN_VERDICTS,
        "alerts": alerts(patient.full_name, records, homework, registered_at=_iso(patient.created_at), unrated=unrated),
        "daf_delay_ms": patient.daf_delay_ms,
    }


# ============================================================================= therapist controls
class GoalIn(BaseModel):
    metric: str
    target: float = Field(ge=0, le=100)


@router.post("/api/v1/admin/patients/{patient_id}/goals", tags=["therapist"])
def add_goal(patient_id: str, body: GoalIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4.therapist import GOAL_METRICS

    patient = therapist_patient(db, user, patient_id)
    if body.metric not in GOAL_METRICS:
        raise HTTPException(status_code=422, detail=f"metric must be one of {', '.join(GOAL_METRICS)}")
    goal = TherapyGoal(patient_id=patient.id, metric=body.metric, target=body.target, created_by_user_id=user.id)
    db.add(goal)
    db.commit()
    return {"id": goal.id, "metric": goal.metric, "target": goal.target}


@router.delete("/api/v1/admin/patients/{patient_id}/goals/{goal_id}", tags=["therapist"], status_code=204)
def remove_goal(patient_id: str, goal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = therapist_patient(db, user, patient_id)
    goal = db.get(TherapyGoal, goal_id)
    if goal is None or goal.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    shared: bool = True


@router.post("/api/v1/admin/patients/{patient_id}/notes", tags=["therapist"])
def add_note(patient_id: str, body: NoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = therapist_patient(db, user, patient_id)
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="The note is empty")
    note = TherapyNote(patient_id=patient.id, author_user_id=user.id, author_name=user.full_name,
                       text=body.text.strip(), shared=body.shared)
    db.add(note)
    db.commit()
    return _note_out(note)


class HomeworkIn(BaseModel):
    due: date | None = None
    times: int = Field(default=1, ge=1, le=20)


@router.patch("/api/v1/admin/patients/{patient_id}/homework/{exercise_id}", tags=["therapist"])
def set_homework(patient_id: str, exercise_id: str, body: HomeworkIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    patient = therapist_patient(db, user, patient_id)
    if exercise_id not in (patient.assigned_exercises or []):
        raise HTTPException(status_code=404, detail="Assign the exercise first")
    row = db.scalar(select(TherapyHomework).where(TherapyHomework.patient_id == patient.id,
                                                  TherapyHomework.exercise_id == exercise_id))
    if row is None:
        row = TherapyHomework(patient_id=patient.id, exercise_id=exercise_id, assigned_by_user_id=user.id)
        db.add(row)
    row.due, row.times = body.due, body.times
    db.commit()
    return {"exercise_id": exercise_id, "due": row.due.isoformat() if row.due else None, "times": row.times}


class RatingIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=1000)


@router.put("/api/v1/admin/attempts/{attempt_id}/rating", tags=["therapist"])
def rate_attempt(attempt_id: int, body: RatingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.get(TherapyAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    therapist_patient(db, user, attempt.patient_id)
    row = db.scalar(select(AttemptRating).where(AttemptRating.attempt_id == attempt_id,
                                                AttemptRating.rater_user_id == user.id))
    if row is None:
        row = AttemptRating(attempt_id=attempt_id, rater_user_id=user.id, rating=body.rating)
        db.add(row)
    row.rating, row.note, row.created_at = body.rating, (body.note or "").strip() or None, utcnow()
    db.commit()
    return {"attempt_id": attempt_id, "rating": row.rating, "app_score": attempt.score}


class PlanReviewIn(BaseModel):
    verdict: str
    note: str | None = Field(default=None, max_length=1000)


@router.post("/api/v1/admin/patients/{patient_id}/plan-review", tags=["therapist"])
def review_plan(patient_id: str, body: PlanReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4.evaluation import PLAN_VERDICTS

    patient = therapist_patient(db, user, patient_id)
    if body.verdict not in PLAN_VERDICTS:
        raise HTTPException(status_code=422, detail=f"verdict must be one of {', '.join(PLAN_VERDICTS)}")
    profile = _require_profile(db, patient.id)
    plan = _plan(db, profile, _records(db, patient.id), patient)
    snapshot = {"level": plan["level"]["label"], "focus": plan["focus"]["key"], "context": plan["engine"]["context"],
                "today": [{k: e.get(k) for k in ("id", "title", "type", "source", "predicted_score", "confidence")}
                          for e in plan["today"]]}
    review = PlanReview(patient_id=patient.id, reviewer_user_id=user.id, verdict=body.verdict,
                        note=(body.note or "").strip() or None, plan_json=json.dumps(snapshot))
    db.add(review)
    db.commit()
    return {"id": review.id, "verdict": review.verdict, "label": PLAN_VERDICTS[review.verdict]}


# ============================================================================= patient: notes, DAF, privacy, export
@router.get("/api/v1/therapy/{patient_id}/notes", tags=["therapy"])
def my_notes(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    notes = db.scalars(select(TherapyNote).where(TherapyNote.patient_id == patient.id, TherapyNote.shared.is_(True))
                       .order_by(TherapyNote.created_at.desc(), TherapyNote.id.desc())).all()
    out = [_note_out(n, patient.notes_read_at) for n in notes]
    for n in out:
        n.pop("shared")
    return {"notes": out, "unread": sum(1 for n in out if n["unread"])}


@router.post("/api/v1/therapy/{patient_id}/notes/read", tags=["therapy"])
def read_notes(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    patient.notes_read_at = utcnow()
    db.commit()
    return my_notes(patient_id, user, db)


class DafTrial(BaseModel):
    delay_ms: int = Field(ge=20, le=500)
    stutter_events: int = Field(ge=0, le=200)
    speech_rate_wpm: float = Field(ge=0, le=400)


class DafCalibrationIn(BaseModel):
    trials: list[DafTrial] = Field(min_length=1, max_length=10)


@router.post("/api/v1/therapy/{patient_id}/daf/calibrate", tags=["therapy"])
def daf_calibrate(patient_id: str, body: DafCalibrationIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    from component4.privacy import calibrate_daf

    patient = get_owned_patient(db, user, patient_id)
    result = calibrate_daf([t.model_dump() for t in body.trials])
    patient.daf_delay_ms = result["recommended_delay_ms"]
    db.commit()
    return result


def _ledger_spent(db: Session) -> float:
    return float(db.scalar(select(func.coalesce(func.sum(PrivacyLedgerEntry.epsilon), 0.0))
                           .where(PrivacyLedgerEntry.ledger_id == COHORT_LEDGER)) or 0.0)


@router.get("/api/v1/therapy/{patient_id}/privacy", tags=["therapy"])
def my_privacy(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4.privacy import budget_status

    patient = get_owned_patient(db, user, patient_id)
    count = lambda model: db.scalar(select(func.count()).select_from(model).where(model.patient_id == patient.id)) or 0  # noqa: E731
    return {
        "stored": [
            {"label": "Practice results", "count": count(TherapyAttempt),
             "detail": "Time, pauses, speaking speed, voice activity, your rating and the score - numbers only."},
            {"label": "Screenings", "count": count(ScreeningSession),
             "detail": "Scores and transcripts from your screenings. The recordings were deleted right after analysis."},
            {"label": "Assistant questions", "count": count(AssistantMessage),
             "detail": "Questions you asked the AI assistant and its answers."},
            {"label": "Notes from your therapist", "count": db.scalar(
                select(func.count()).select_from(TherapyNote).where(TherapyNote.patient_id == patient.id,
                                                                    TherapyNote.shared.is_(True))) or 0,
             "detail": "Notes your therapist chose to share with you."},
        ],
        "never_stored": [
            "Audio from therapy exercises - your voice is analysed in this browser and never uploaded.",
            "Screening recordings after analysis - they are deleted from the server straight away.",
        ],
        "cohort_privacy": {
            **budget_status(_ledger_spent(db)),
            "explanation": ("When the clinic shares statistics about all patients (for research or reports), "
                            "random noise is added with differential privacy so nobody can work out one person's "
                            "results. Each release uses part of a fixed privacy budget (ε)."),
        },
        "assistant_ai": ("If the optional AI model answers a question, it only receives a short summary of your "
                         "practice numbers - never your name, recordings or screening details."),
    }


@router.get("/api/v1/therapy/{patient_id}/export", tags=["therapy"])
def export_my_data(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    records = _records(db, patient.id)
    learner = _learner(db, patient)
    chats = db.scalars(select(AssistantMessage).where(AssistantMessage.patient_id == patient.id)
                       .order_by(AssistantMessage.created_at)).all()
    data = {
        "exported_at": _iso(utcnow()),
        "patient": {"id": patient.id, "full_name": patient.full_name, "age": patient.age},
        "practice_results": [{k: v for k, v in r.items() if k not in ("focus", "score_breakdown")} for r in records],
        "homework": learner["homework"],
        "notes_from_therapist": my_notes(patient_id, user, db)["notes"],
        "assistant_questions": [{"question": c.question, "reply": c.reply, "at": _iso(c.created_at)} for c in chats],
        "daf_delay_ms": patient.daf_delay_ms,
    }
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="speakfree-therapy-{patient.id}.json"'})


# ============================================================================= usability survey
class SurveyIn(BaseModel):
    answers: list[int] = Field(min_length=10, max_length=10)
    comment: str | None = Field(default=None, max_length=1000)


@router.get("/api/v1/survey", tags=["survey"])
def survey_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4.evaluation import SUS_BENCHMARK, SUS_INVITE_AFTER, SUS_ITEMS, sus_band

    mine = db.scalar(select(UsabilitySurvey).where(UsabilitySurvey.user_id == user.id))
    if user.role in ("admin", "clinician"):
        eligible = True
    else:
        ids = [p.id for p in user.patients]
        done = db.scalar(select(func.count()).select_from(TherapyAttempt).where(TherapyAttempt.patient_id.in_(ids))) if ids else 0
        eligible = (done or 0) >= SUS_INVITE_AFTER
    return {"items": SUS_ITEMS, "benchmark": SUS_BENCHMARK, "responded": mine is not None,
            "score": mine.score if mine else None, "band": sus_band(mine.score) if mine else None,
            "invite": eligible and mine is None}


@router.post("/api/v1/survey", tags=["survey"])
def submit_survey(body: SurveyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from component4.evaluation import sus_band, sus_score

    try:
        score = sus_score(body.answers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = db.scalar(select(UsabilitySurvey).where(UsabilitySurvey.user_id == user.id))
    if row is None:
        row = UsabilitySurvey(user_id=user.id, role=user.role, answers=body.answers, score=score)
        db.add(row)
    row.role, row.answers, row.score = user.role, body.answers, score
    row.comment, row.submitted_at = (body.comment or "").strip() or None, utcnow()
    db.commit()
    return {"score": score, "band": sus_band(score)}


# ============================================================================= admin: evidence
@router.get("/api/v1/admin/evidence", tags=["admin: evidence"])
def evidence(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    from component4.evaluation import agreement, inter_rater, plan_review_stats, sus_summary
    from component4.privacy import FEDERATED_DESIGN, budget_status
    from component4.scoring import FEATURE_LABELS, THRESHOLDS, WEIGHTS

    rows = db.execute(select(AttemptRating, TherapyAttempt).join(TherapyAttempt, AttemptRating.attempt_id == TherapyAttempt.id)
                      .order_by(AttemptRating.attempt_id, AttemptRating.id)).all()
    rated, by_attempt, records = [], {}, {}
    for rating, attempt in rows:
        record = records.setdefault(attempt.id, json.loads(attempt.record_json))
        rated.append({"record": record, "score": attempt.score, "rating": rating.rating})
        by_attempt.setdefault(attempt.id, []).append(rating.rating)
    reviews = db.scalars(select(PlanReview).order_by(PlanReview.created_at.desc())).all()
    names = {p.id: p.full_name for p in db.scalars(select(Patient).where(Patient.id.in_({r.patient_id for r in reviews})))} if reviews else {}
    surveys = db.scalars(select(UsabilitySurvey)).all()
    ledger = db.scalars(select(PrivacyLedgerEntry).where(PrivacyLedgerEntry.ledger_id == COHORT_LEDGER)
                        .order_by(PrivacyLedgerEntry.created_at.desc())).all()
    return {
        "agreement": agreement(rated),
        "inter_rater": inter_rater(by_attempt),
        "scatter": [{"score": r["score"], "rating": r["rating"], "type": r["record"]["exercise_type"]} for r in rated],
        "plan_reviews": {**plan_review_stats([r.verdict for r in reviews]),
                         "recent": [{"patient": names.get(r.patient_id, r.patient_id), "verdict": r.verdict, "note": r.note,
                                     "at": _iso(r.created_at), "plan": json.loads(r.plan_json)} for r in reviews[:10]]},
        "usability": sus_summary([{"role": s.role, "answers": s.answers, "score": s.score, "comment": s.comment,
                                   "submitted_at": _iso(s.submitted_at)} for s in surveys]),
        "scoring": {"weights": [{"feature": f, "label": FEATURE_LABELS[f], "weight": w} for f, w in WEIGHTS.items()],
                    "thresholds": THRESHOLDS},
        "privacy": {**budget_status(_ledger_spent(db)),
                    "releases": [{"epsilon": e.epsilon, "at": _iso(e.created_at)} for e in ledger[:20]]},
        "federated": FEDERATED_DESIGN,
    }


@router.get("/api/v1/admin/evidence/cohort", tags=["admin: evidence"])
def cohort_report(epsilon: float = Query(1.0), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    from component4.adaptive import learner_bracket
    from component4.privacy import EPSILON_OPTIONS, budget_status, fingerprint, release, true_stats
    from component4.progress import TYPE_LABELS

    if epsilon not in EPSILON_OPTIONS:
        raise HTTPException(status_code=422, detail=f"epsilon must be one of {EPSILON_OPTIONS}")
    attempts = db.scalars(select(TherapyAttempt)).all()
    records = [json.loads(a.record_json) for a in attempts]
    levels = []
    for pid in db.scalars(select(TherapyProfile.patient_id).distinct()).all():
        patient = db.get(Patient, pid)
        profile = _active_profile(db, pid)
        if patient and profile:
            levels.append(learner_bracket(profile, _records(db, pid), _learner(db, patient))["bracket"])
    stats = true_stats(records, levels, TYPE_LABELS)
    fp = fingerprint([a.id for a in attempts] + levels)
    key = f"{fp}:{epsilon}"
    if db.scalar(select(PrivacyLedgerEntry).where(PrivacyLedgerEntry.release_key == key)) is None:
        if _ledger_spent(db) + epsilon > budget_status(0)["epsilon_threshold"]:
            raise HTTPException(status_code=409, detail="The privacy budget for cohort releases is used up.")
        db.add(PrivacyLedgerEntry(ledger_id=COHORT_LEDGER, release_key=key, epsilon=epsilon, created_by_user_id=user.id))
        db.commit()
    return {**release(stats, epsilon, fp, TYPE_LABELS), "budget": budget_status(_ledger_spent(db)),
            "epsilon_options": EPSILON_OPTIONS}
