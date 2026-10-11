from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.therapy import auth
from app.therapy.adaptive import LEVELS
from app.therapy.cohort_report import EPSILON_OPTIONS, release
from app.therapy.exercises import get_exercise
from app.therapy.intent_classifier import leave_one_out_accuracy
from app.therapy.progress_store import get_records, update_record
from app.therapy.scoring import calibrate, model_report, rated_attempts
from app.therapy.simulation import evaluate
from app.therapy.therapist import caseload_overview, list_students, student_detail
from app.therapy.therapist_store import (
    GOAL_METRICS,
    add_goal,
    add_note,
    remove_goal,
    set_assigned,
    set_level_override,
)
from app.therapy.user_store import create_user, get_user, public, update_user

router = APIRouter(prefix="/api/v1", tags=["auth & therapist"])


# --- Authentication ----------------------------------------------------------

class SignupRequest(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=6)
    role: str = "student"
    invite_code: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


def _session(user: dict) -> dict:
    return {"token": auth.issue_token(user), "user": public(user)}


@router.post("/auth/signup")
async def signup(payload: SignupRequest):
    role = "therapist" if payload.role == "therapist" else "student"
    if role == "therapist" and payload.invite_code != auth.THERAPIST_INVITE_CODE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A valid clinic invite code is required for therapist accounts.")
    existing = get_user(payload.email)
    if existing and existing.get("password_hash"):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Please log in.")
    user = create_user(payload.email, payload.name, role, auth.hash_password(payload.password))
    if existing:  # keep the original registration date for pre-password accounts
        user = update_user(payload.email, {"registered_at": existing["registered_at"]})
    return _session(user)


@router.post("/auth/login")
async def login(payload: LoginRequest):
    user = get_user(payload.email)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    now = datetime.now(timezone.utc).isoformat()
    if not user.get("password_hash"):
        # Account from before passwords existed: the first login sets the password.
        user = update_user(payload.email, {"password_hash": auth.hash_password(payload.password), "last_login": now})
    elif not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    else:
        user = update_user(payload.email, {"last_login": now})
    return _session(user)


@router.get("/auth/me")
async def me(user: dict = Depends(auth.current_user)):
    account = get_user(user["email"])
    if account is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found.")
    return public(account)


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

class AssignRequest(BaseModel):
    exercise_ids: list[str]


class LevelRequest(BaseModel):
    level: str | None


class GoalRequest(BaseModel):
    metric: str
    target: float


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ExpertRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    note: str | None = None


@router.put("/therapist/students/{email}/assigned")
async def assign_exercises(email: str, payload: AssignRequest, user: dict = Depends(auth.require_therapist)):
    unknown = [e for e in payload.exercise_ids if get_exercise(e) is None]
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown exercises: {', '.join(unknown)}")
    return set_assigned(email, payload.exercise_ids, user["email"])


@router.put("/therapist/students/{email}/level")
async def override_level(email: str, payload: LevelRequest, user: dict = Depends(auth.require_therapist)):
    if payload.level is not None and payload.level not in LEVELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown level")
    return set_level_override(email, payload.level, user["email"])


@router.post("/therapist/students/{email}/goals")
async def create_goal(email: str, payload: GoalRequest, user: dict = Depends(auth.require_therapist)):
    if payload.metric not in GOAL_METRICS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown goal metric")
    return add_goal(email, payload.metric, payload.target, user["email"])


@router.delete("/therapist/students/{email}/goals/{goal_id}")
async def delete_goal(email: str, goal_id: str, _: dict = Depends(auth.require_therapist)):
    return remove_goal(email, goal_id)


@router.post("/therapist/students/{email}/notes")
async def create_note(email: str, payload: NoteRequest, user: dict = Depends(auth.require_therapist)):
    return add_note(email, payload.text, user["email"])


@router.put("/therapist/students/{email}/records/{record_id}/rating")
async def rate_attempt(
    email: str, record_id: str, payload: ExpertRatingRequest, user: dict = Depends(auth.require_therapist)
):
    """Expert validation: the therapist's 1–5 rating of one attempt. Saving
    a rating re-runs calibration of the scoring model."""
    record = update_record(
        email,
        record_id,
        {
            "expert": {
                "rating": payload.rating,
                "note": (payload.note or "").strip() or None,
                "by": user["email"],
                "at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    calibration = calibrate()
    return {"record": record, "calibration": {k: calibration[k] for k in ("active", "n_ratings", "thresholds")}}


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
            }
            for r in rated
        ],
        "assistant": leave_one_out_accuracy(),
        "adaptive": evaluate(),
    }


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
