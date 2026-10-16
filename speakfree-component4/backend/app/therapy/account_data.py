"""
The user's rights over their own data (Sri Lanka Personal Data Protection
Act No. 9 of 2022: access, and erasure): download everything stored about
an account, or delete it.

Deleting a student removes their account, practice records (with any expert
ratings on them), therapist settings, plan reviews and survey response, then
re-fits the scoring calibration without their ratings. The audit log keeps
only the fact that a deletion happened.
"""

import json
from datetime import datetime, timezone

from app.therapy import appointments, messages, plan_review, progress_store, survey, therapist_store, user_store
from app.therapy.progress_store import normalize_user_id
from app.therapy.scoring import calibrate


def export(email: str) -> dict:
    uid = normalize_user_id(email)
    account = user_store.get_user(uid)
    surveys = [r for r in survey._load() if r["user_id"] == uid]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": user_store.public(account) if account else None,
        "practice_records": progress_store.get_records(uid),
        "therapist_settings": therapist_store.get_settings(uid),
        "plan_reviews": plan_review.reviews_for(uid),
        "survey_responses": surveys,
        "messages": messages.thread(uid, "student")["messages"],
        "appointments": appointments.for_student(uid)["booked"],
        "not_stored": "Voice recordings are never saved or uploaded.",
    }


def _rewrite(path, keep) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if keep(k)} if isinstance(data, dict) else [r for r in data if keep(r)]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def delete(email: str) -> dict:
    uid = normalize_user_id(email)
    with progress_store._lock:
        _rewrite(progress_store.DATA_FILE, lambda k: k != uid)
    with user_store._lock:
        _rewrite(user_store.USERS_FILE, lambda k: k != uid)
    with therapist_store._lock:
        _rewrite(therapist_store.STORE_FILE, lambda k: k != uid)
    with plan_review._lock:
        _rewrite(plan_review.REVIEWS_FILE, lambda r: r["student"] != uid)
    with survey._lock:
        _rewrite(survey.SURVEY_FILE, lambda r: r["user_id"] != uid)
    messages.delete_student(uid)
    appointments.delete_student(uid)
    calibrate()
    return {"deleted": uid}
