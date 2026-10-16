import csv
import io
import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.therapy import account_data, appointments, audit, auth, messages, pilot, plan_review
from app.therapy.adaptive import LEVELS, personal_target_wpm
from app.therapy.assistant import answer
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.cohort_report import EPSILON_OPTIONS, release
from app.therapy.dashboard import build_progress_summary
from app.therapy.exercises import EXERCISE_BANK, get_exercise
from app.therapy.intent_classifier import leave_one_out_accuracy
from app.therapy.progress_store import get_records, normalize_user_id, update_record
from app.therapy.scoring import calibrate, model_report, rated_attempts, rating_source, reviews_of
from app.therapy.simulation import evaluate
from app.therapy import survey
from app.therapy.therapist import caseload_overview, list_students, student_detail
from app.therapy.therapist_store import (
    GOAL_METRICS,
    add_goal,
    add_note,
    get_settings,
    remove_goal,
    set_assigned,
    set_level_override,
)
from app.therapy.user_store import (
    AGE_GROUPS,
    GUARDIAN_CONSENT_UNDER,
    age_group_for,
    age_group_of,
    create_user,
    get_user,
    is_demo_account,
    public,
    update_user,
)

router = APIRouter(prefix="/api/v1", tags=["auth & therapist"])


# --- Authentication ----------------------------------------------------------

class SignupRequest(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=6)
    role: str = "student"
    invite_code: str | None = None
    # Informed consent to store practice results (PDPA No. 9 of 2022).
    consent: bool = False
    # Students only: age decides the practice group; under 18 needs a guardian's agreement.
    age: int | None = None
    guardian_consent: bool = False


class AgeRequest(BaseModel):
    age: int
    guardian_consent: bool = False


def _age_fields(age: int | None, guardian_consent: bool) -> dict:
    """Validates a student's age and returns the fields to store."""
    if age is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please enter your age.")
    try:
        group = age_group_for(age)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if age < GUARDIAN_CONSENT_UNDER and not guardian_consent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A parent or guardian must agree to this account for anyone under 18."
        )
    fields = {"age": age, "age_group": group}
    if age < GUARDIAN_CONSENT_UNDER:
        fields["guardian_consent_at"] = datetime.now(timezone.utc).isoformat()
    return fields


class LoginRequest(BaseModel):
    email: str
    password: str


def _session(user: dict) -> dict:
    return {"token": auth.issue_token(user), "user": public(user)}


@router.post("/auth/signup")
async def signup(payload: SignupRequest):
    role = "therapist" if payload.role == "therapist" else "student"
    if not payload.consent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Please read and agree to how your data is used before creating an account."
        )
    age_fields = _age_fields(payload.age, payload.guardian_consent) if role == "student" else {}
    if role == "therapist" and payload.invite_code != auth.THERAPIST_INVITE_CODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A valid clinic invite code is required for therapist accounts.")
    existing = get_user(payload.email)
    if existing and existing.get("password_hash"):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Please log in.")
    user = create_user(payload.email, payload.name, role, auth.hash_password(payload.password))
    if existing:  # keep the original registration date for pre-password accounts
        user = update_user(payload.email, {"registered_at": existing["registered_at"]})
    user = update_user(
        payload.email,
        {"consent": {"version": CONSENT_VERSION, "at": datetime.now(timezone.utc).isoformat()}, **age_fields},
    )
    return _session(user)


@router.post("/auth/login")
async def login(payload: LoginRequest):
    wait = auth.login_blocked_for(payload.email)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {max(1, wait // 60)} minute(s).",
        )
    user = get_user(payload.email)
    if user is None:
        auth.record_failed_login(payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    now = datetime.now(timezone.utc).isoformat()
    if not user.get("password_hash"):
        # Account from before passwords existed: the first login sets the password.
        user = update_user(payload.email, {"password_hash": auth.hash_password(payload.password), "last_login": now})
    elif not auth.verify_password(payload.password, user["password_hash"]):
        auth.record_failed_login(payload.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    else:
        auth.clear_failed_logins(payload.email)
        user = update_user(payload.email, {"last_login": now})
    return _session(user)


@router.put("/auth/me/age")
async def set_my_age(payload: AgeRequest, user: dict = Depends(auth.current_user)):
    """One-time step for students who signed up before ages were collected."""
    if user["role"] != "student":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only student accounts have an age group.")
    account = update_user(user["email"], _age_fields(payload.age, payload.guardian_consent))
    audit.log(user["email"], "age.set", user["email"], age_group=account["age_group"])
    return public(account)


@router.get("/auth/me")
async def me(user: dict = Depends(auth.current_user)):
    account = get_user(user["email"])
    if account is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found.")
    return public(account)


# --- Your data: download and delete (PDPA No. 9 of 2022) -------------------------

CONSENT_VERSION = "2026-10"


@router.get("/auth/me/data")
async def download_my_data(user: dict = Depends(auth.current_user)):
    """Everything stored about the logged-in account, as JSON."""
    return Response(
        json.dumps(account_data.export(user["email"]), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="speakfree-my-data.json"'},
    )


@router.delete("/auth/me")
async def delete_my_account(user: dict = Depends(auth.current_user)):
    """Permanently deletes the account and every result stored for it."""
    result = account_data.delete(user["email"])
    audit.log(user["email"], "account.deleted", user["email"])
    return result


# --- Messages between student and therapist ---------------------------------------

class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=messages.MAX_LENGTH)


def _named(thread: dict) -> dict:
    for m in thread["messages"]:
        sender = get_user(m["from"])
        m["from_name"] = sender["name"] if sender else m["from"]
    return thread


@router.get("/messages/{student}")
async def get_messages(student: str, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, student)
    return _named(messages.thread(student, user["role"]))


@router.post("/messages/{student}")
async def post_message(student: str, payload: MessageRequest, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, student)
    audit.log(user["email"], "message.sent", normalize_user_id(student))
    try:
        return _named(messages.send(student, user["email"], user["role"], payload.text))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/messages/{student}/read")
async def read_messages(student: str, user: dict = Depends(auth.current_user)):
    auth.ensure_can_access(user, student)
    return _named(messages.mark_read(student, user["role"]))


# --- Appointments ----------------------------------------------------------------

class SlotRequest(BaseModel):
    start: datetime  # ISO 8601 with timezone, e.g. 2026-10-20T09:30:00+05:30
    minutes: int = Field(default=30, ge=10, le=180)
    mode: str = "clinic"
    student: str | None = None  # book straight away for this student


def _named_slot(slot: dict) -> dict:
    therapist = get_user(slot["therapist"])
    student = get_user(slot["student"]) if slot["student"] else None
    return {
        **slot,
        "therapist_name": therapist["name"] if therapist else slot["therapist"],
        "student_name": student["name"] if student else slot["student"],
    }


@router.get("/appointments")
async def list_appointments(user: dict = Depends(auth.current_user)):
    if user["role"] == "therapist":
        return {"sessions": [_named_slot(s) for s in appointments.for_therapist()]}
    data = appointments.for_student(user["email"])
    return {"booked": [_named_slot(s) for s in data["booked"]], "open": [_named_slot(s) for s in data["open"]]}


@router.post("/appointments/slots")
async def create_slot(payload: SlotRequest, user: dict = Depends(auth.require_therapist)):
    try:
        slot = appointments.create_slot(user["email"], payload.start, payload.minutes, payload.mode, payload.student)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    audit.log(user["email"], "appointment.created", slot["student"], start=slot["start"])
    return _named_slot(slot)


@router.post("/appointments/{slot_id}/book")
async def book_appointment(slot_id: str, user: dict = Depends(auth.current_user)):
    if user["role"] != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only students book sessions.")
    try:
        slot = appointments.book(slot_id, user["email"])
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    audit.log(user["email"], "appointment.booked", user["email"], start=slot["start"])
    return _named_slot(slot)


@router.post("/appointments/{slot_id}/cancel")
async def cancel_appointment(slot_id: str, user: dict = Depends(auth.current_user)):
    try:
        slot = appointments.cancel(slot_id, user["email"], user["role"])
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    audit.log(user["email"], "appointment.cancelled", slot["student"], start=slot["start"])
    return _named_slot(slot)


# --- Usability survey (SUS) -----------------------------------------------------

class SurveyRequest(BaseModel):
    answers: list[int] = Field(min_length=10, max_length=10)
    comment: str | None = Field(default=None, max_length=2000)


@router.get("/survey/status")
async def survey_status(user: dict = Depends(auth.current_user)):
    sessions = len(get_records(user["email"]))
    responded = survey.has_responded(user["email"])
    eligible = user["role"] == "therapist" or sessions >= survey.SESSIONS_BEFORE_INVITE
    return {
        "items": survey.ITEMS,
        "responded": responded,
        "eligible": eligible,
        "invite": eligible and not responded,
        "sessions": sessions,
        "sessions_needed": survey.SESSIONS_BEFORE_INVITE,
    }


@router.post("/survey")
async def submit_survey(payload: SurveyRequest, user: dict = Depends(auth.current_user)):
    try:
        return survey.submit(user["email"], user["role"], payload.answers, payload.comment)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


# --- Therapist: caseload --------------------------------------------------------

@router.get("/therapist/overview")
async def therapist_overview(_: dict = Depends(auth.require_therapist)):
    return caseload_overview()


@router.get("/therapist/students")
async def therapist_students(_: dict = Depends(auth.require_therapist)):
    return list_students()


@router.get("/therapist/students/{email}")
async def therapist_student(email: str, _: dict = Depends(auth.require_therapist)):
    detail = student_detail(email)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return detail


# --- Therapist: controls ---------------------------------------------------------

class AssignmentItem(BaseModel):
    exercise_id: str
    due: date | None = None
    times: int = Field(default=1, ge=1, le=14)


class AssignRequest(BaseModel):
    # Either plain exercise ids (no due date, once each) or items with homework details.
    exercise_ids: list[str] = []
    items: list[AssignmentItem] | None = None


class LevelRequest(BaseModel):
    level: str | None


class AgeGroupRequest(BaseModel):
    age_group: str


class GoalRequest(BaseModel):
    metric: str
    target: float


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    shared: bool = True  # show to the student (with a notification)


class ExpertRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    note: str | None = None
    # A second rater at the same sitting (sharing this login) gives their name,
    # so their rating is kept separately for inter-rater agreement.
    rater: str | None = Field(default=None, max_length=80)
    # True when rated in a validation session while listening to the recording.
    heard_audio: bool = False


@router.put("/therapist/students/{email}/assigned")
async def assign_exercises(email: str, payload: AssignRequest, user: dict = Depends(auth.require_therapist)):
    items = (
        [{"exercise_id": i.exercise_id, "due": i.due.isoformat() if i.due else None, "times": i.times}
         for i in payload.items]
        if payload.items is not None
        else [{"exercise_id": e} for e in payload.exercise_ids]
    )
    unknown = [i["exercise_id"] for i in items if get_exercise(i["exercise_id"]) is None]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown exercises: {', '.join(unknown)}")
    audit.log(user["email"], "exercises.assigned", normalize_user_id(email), items=items)
    return set_assigned(email, items, user["email"])


@router.put("/therapist/students/{email}/age-group")
async def set_student_age_group(email: str, payload: AgeGroupRequest, user: dict = Depends(auth.require_therapist)):
    """The therapist can move a student to another age group (e.g. a mature
    13-year-old to teen tasks); the student's age itself is unchanged."""
    if payload.age_group not in AGE_GROUPS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"age_group must be one of {', '.join(AGE_GROUPS)}")
    account = update_user(email, {"age_group": payload.age_group, "age_group_set_by": user["email"]})
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    audit.log(user["email"], "age_group.set", normalize_user_id(email), age_group=payload.age_group)
    return public(account)


@router.put("/therapist/students/{email}/level")
async def override_level(email: str, payload: LevelRequest, user: dict = Depends(auth.require_therapist)):
    if payload.level is not None and payload.level not in LEVELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown level")
    audit.log(user["email"], "level.set", normalize_user_id(email), level=payload.level)
    return set_level_override(email, payload.level, user["email"])


@router.post("/therapist/students/{email}/goals")
async def create_goal(email: str, payload: GoalRequest, user: dict = Depends(auth.require_therapist)):
    if payload.metric not in GOAL_METRICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown goal metric")
    audit.log(user["email"], "goal.added", normalize_user_id(email), metric=payload.metric, target=payload.target)
    return add_goal(email, payload.metric, payload.target, user["email"])


@router.delete("/therapist/students/{email}/goals/{goal_id}")
async def delete_goal(email: str, goal_id: str, user: dict = Depends(auth.require_therapist)):
    audit.log(user["email"], "goal.removed", normalize_user_id(email), goal_id=goal_id)
    return remove_goal(email, goal_id)


@router.post("/therapist/students/{email}/notes")
async def create_note(email: str, payload: NoteRequest, user: dict = Depends(auth.require_therapist)):
    audit.log(user["email"], "note.added", normalize_user_id(email), shared=payload.shared)
    return add_note(email, payload.text, user["email"], payload.shared)


@router.put("/therapist/students/{email}/records/{record_id}/rating")
async def rate_attempt(
    email: str, record_id: str, payload: ExpertRatingRequest, user: dict = Depends(auth.require_therapist)
):
    """Expert validation: the therapist's 1–5 rating of one attempt. Each
    rater's review is kept separately (for inter-rater agreement); the first
    rater's review is the one calibration uses. Saving a rating re-runs
    calibration of the scoring model."""
    existing = next((r for r in get_records(email) if r["id"] == record_id), None)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    rater_name = (payload.rater or "").strip()
    rater_id = f"{rater_name} (via {user['email']})" if rater_name else user["email"]
    review = {
        "rating": payload.rating,
        "note": (payload.note or "").strip() or None,
        "by": rater_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "source": "synthetic" if is_demo_account(user["email"]) else "clinician",
        "heard_audio": payload.heard_audio,
    }
    reviews = {r["by"]: r for r in reviews_of(existing)}
    reviews[rater_id] = review
    record = update_record(
        email, record_id, {"expert": next(iter(reviews.values())), "expert_reviews": reviews}
    )
    audit.log(user["email"], "attempt.rated", normalize_user_id(email), record_id=record_id, rating=payload.rating)
    calibration = calibrate()
    return {"record": record, "calibration": {k: calibration[k] for k in ("active", "n_ratings", "thresholds")}}


class PlanReviewRequest(BaseModel):
    verdict: str
    note: str | None = Field(default=None, max_length=2000)


@router.post("/therapist/students/{email}/plan-review")
async def review_plan(email: str, payload: PlanReviewRequest, user: dict = Depends(auth.require_therapist)):
    """Expert validation of the adaptive output: the therapist's judgement of
    the weekly plan currently generated for this student."""
    plan = recommend_weekly_plan(get_records(email), get_settings(email), age_group=age_group_of(email))
    audit.log(user["email"], "plan.reviewed", normalize_user_id(email), verdict=payload.verdict)
    try:
        return plan_review.add_review(email, plan, payload.verdict, payload.note, user["email"])
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


# --- Therapist: evidence -----------------------------------------------------------

@router.get("/therapist/evidence")
async def evidence(_: dict = Depends(auth.require_therapist)):
    rated = rated_attempts()
    return {
        "scoring": model_report(),
        "ratings": [
            {
                "student": r["user_id"],
                "title": r["title"],
                "completed_at": r["completed_at"],
                "auto_score": r["score"],
                "expert_rating": r["expert"]["rating"],
                "expert_score": (r["expert"]["rating"] - 1) * 25,
                "source": rating_source(r["expert"]),
            }
            for r in rated
        ],
        "plan_validation": plan_review.summary(),
        "pilot": pilot.report(),
        "assistant": leave_one_out_accuracy(),
        "adaptive": evaluate(),
        "usability": survey.summary(),
    }


@router.get("/therapist/evidence/ratings.csv")
async def ratings_sheet(_: dict = Depends(auth.require_therapist)):
    """Every expert rating as a spreadsheet — the rating sheet for the report."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["student", "attempt_id", "exercise", "exercise_type", "completed_at", "app_score",
         "rater", "rating_1_to_5", "source", "heard_audio", "rated_at", "note"]
    )
    for r in rated_attempts():
        for review in reviews_of(r):
            writer.writerow(
                [r["user_id"], r["id"], r["title"], r["exercise_type"], r["completed_at"], r["score"],
                 review.get("by"), review["rating"], rating_source(review), bool(review.get("heard_audio")),
                 review.get("at"), review.get("note") or ""]
            )
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="expert-ratings.csv"'},
    )


@router.get("/therapist/evidence/pilot.csv")
async def pilot_sheet(_: dict = Depends(auth.require_therapist)):
    """Pilot study, one row per participant: first week vs last week."""
    data = pilot.report()
    out = io.StringIO()
    columns = ["student", "name", "included", "reason", "span_days", "attempts", "first_week_attempts",
               "last_week_attempts", "first_week_score", "last_week_score", "change",
               "first_week_pauses", "last_week_pauses"]
    writer = csv.writer(out)
    writer.writerow(columns)
    for row in data["participants"]:
        writer.writerow([row[c] if row[c] is not None else "" for c in columns])
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pilot-study.csv"'},
    )


# --- Therapist: side-by-side comparison -------------------------------------------

COMPARE_QUESTION = "What should I practise next?"


def _compare_column(email: str) -> dict:
    records = get_records(email)
    settings = get_settings(email)
    profile = get_user(email) or {"email": email, "name": email}
    summary = build_progress_summary(normalize_user_id(email), records)
    return {
        "email": profile["email"],
        "name": profile["name"],
        "sessions": len(records),
        "average_score": summary["average_score"],
        "report_card": summary["report_card"],
        "level": summary["level"],
        "plan": recommend_weekly_plan(records, settings, age_group=summary["age_group"]),
        "reading_speeds": [
            {
                "title": ex.title,
                "level": ex.level.value,
                "base_wpm": ex.target_wpm,
                "personal_wpm": personal_target_wpm(ex.target_wpm, ex.id, records, summary["age_group"]),
            }
            for ex in EXERCISE_BANK
            if ex.level is not None and ex.target_wpm and summary["age_group"] in ex.age_groups
        ],
        "assistant": answer(normalize_user_id(email), profile["name"], COMPARE_QUESTION, records),
    }


@router.get("/therapist/compare")
async def compare_students(a: str, b: str, _: dict = Depends(auth.require_therapist)):
    """Two students side by side, to show that levels, plans, reading speeds
    and assistant answers all come from each student's own history."""
    for email in (a, b):
        if get_user(email) is None and not get_records(email):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Student not found: {email}")
    return {"question": COMPARE_QUESTION, "students": [_compare_column(a), _compare_column(b)]}


@router.get("/therapist/audit")
async def audit_log(student: str | None = None, _: dict = Depends(auth.require_therapist)):
    """Who changed what, newest first (optionally for one student)."""
    return audit.recent(subject=normalize_user_id(student) if student else None)


@router.post("/therapist/evidence/recalibrate")
async def recalibrate(_: dict = Depends(auth.require_therapist)):
    return calibrate()


@router.get("/therapist/cohort-report")
async def cohort_report(epsilon: float = 1.0, _: dict = Depends(auth.require_therapist)):
    if epsilon not in EPSILON_OPTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"epsilon must be one of {EPSILON_OPTIONS}")
    return release(epsilon)


@router.get("/therapist/students/{email}/records")
async def student_records(email: str, _: dict = Depends(auth.require_therapist)):
    return get_records(email)
