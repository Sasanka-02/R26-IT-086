"""
Therapist portal — read-only views across all students.

Combines the account registry with each student's practice records to
give a therapist a caseload overview, a student list with plain-language
status, and per-student detail with chart-ready series.
"""

from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import LEVEL_LABELS, LEVELS, verdict
from app.therapy.dashboard import build_progress_summary
from app.therapy.progress_store import all_records, get_records, normalize_user_id
from app.therapy.therapist_store import get_settings
from app.therapy.user_store import get_user, list_users

INACTIVE_DAYS = 7


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _fallback_profile(user_id: str, records: list[dict]) -> dict:
    """Profile for someone with saved work but no registry entry."""
    return {
        "email": user_id,
        "name": user_id.split("@")[0],
        "role": "student",
        "registered_at": records[0]["completed_at"] if records else None,
    }


def _students() -> list[tuple[dict, list[dict]]]:
    """(profile, records) for every student — registered or with saved work."""
    records_by_user = all_records()
    users = {u["email"]: u for u in list_users()}
    profiles = {email: u for email, u in users.items() if u.get("role") != "therapist"}
    for user_id, records in records_by_user.items():
        if user_id not in users:
            profiles[user_id] = _fallback_profile(user_id, records)
    return [(p, records_by_user.get(email, [])) for email, p in profiles.items()]


def _status(summary: dict, records: list[dict], now: datetime) -> dict:
    """One plain-language status per student, most urgent first."""
    if not records:
        return {"key": "not_started", "label": "Not started", "detail": "No exercises saved yet."}
    days_idle = (now - _parse(records[-1]["completed_at"])).days
    if days_idle >= INACTIVE_DAYS:
        return {"key": "inactive", "label": "Inactive", "detail": f"No practice for {days_idle} days."}
    hard = sum(1 for r in records[-5:] if r["self_rating"] == "hard")
    if summary["trend"]["label"] == "Dipped a little" or hard >= 2:
        return {
            "key": "needs_attention",
            "label": "Needs attention",
            "detail": "Recent scores dipped or several exercises felt hard.",
        }
    if summary["trend"]["label"] == "Improving":
        return {"key": "improving", "label": "Improving", "detail": summary["trend"]["detail"]}
    return {"key": "on_track", "label": "On track", "detail": "Practising regularly."}


def _student_row(profile: dict, records: list[dict], now: datetime) -> dict:
    summary = build_progress_summary(profile["email"], records)
    return {
        "email": profile["email"],
        "name": profile["name"],
        "registered_at": profile.get("registered_at"),
        "last_active": records[-1]["completed_at"] if records else None,
        "total_sessions": summary["total_sessions"],
        "total_minutes": summary["total_minutes"],
        "average_score": summary["average_score"],
        "latest_score": records[-1]["score"] if records else None,
        "level": summary["level"]["level"],
        "level_label": summary["level"]["label"],
        "streak_days": summary["streak_days"],
        "status": _status(summary, records, now),
    }


def list_students() -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = [_student_row(p, r, now) for p, r in _students()]
    rows.sort(key=lambda row: row["last_active"] or row["registered_at"] or "", reverse=True)
    return rows


def caseload_overview(days: int = 14) -> dict:
    now = datetime.now(timezone.utc)
    students = _students()
    rows = [_student_row(p, r, now) for p, r in students]
    week_ago = now - timedelta(days=7)
    all_recs = [r for _, recs in students for r in recs]

    # Raw timestamps; the browser buckets them into the viewer's local days.
    since = now - timedelta(days=days + 1)
    recent = sorted(r["completed_at"] for r in all_recs if _parse(r["completed_at"]) >= since)

    scores = [r["score"] for r in all_recs]
    alerts = []
    for row in rows:
        if row["status"]["key"] in ("needs_attention", "inactive"):
            alerts.append(
                {"email": row["email"], "name": row["name"], "status": row["status"]}
            )
        _, recs = next((p, r) for p, r in students if p["email"] == row["email"])
        if len(recs) >= 3 and all(r["self_rating"] == "hard" for r in recs[-3:]):
            alerts.append(
                {
                    "email": row["email"],
                    "name": row["name"],
                    "status": {
                        "key": "needs_attention",
                        "label": "3 hard in a row",
                        "detail": "The last three exercises all felt hard — consider an easier plan.",
                    },
                }
            )
    return {
        "alerts": alerts,
        "total_students": len(rows),
        "active_this_week": sum(
            1 for _, recs in students if recs and _parse(recs[-1]["completed_at"]) >= week_ago
        ),
        "sessions_this_week": sum(1 for r in all_recs if _parse(r["completed_at"]) >= week_ago),
        "total_sessions": len(all_recs),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "needs_attention": sum(
            1 for row in rows if row["status"]["key"] in ("needs_attention", "inactive")
        ),
        "recent_session_times": recent,
        "level_distribution": [
            {
                "level": level,
                "label": LEVEL_LABELS[level],
                "students": sum(1 for row in rows if row["level"] == level),
            }
            for level in LEVELS
        ],
    }


def student_detail(email: str) -> dict | None:
    user_id = normalize_user_id(email)
    profile = get_user(user_id)
    records = get_records(user_id)
    if profile is None and not records:
        return None
    if profile is None:
        profile = _fallback_profile(user_id, records)

    now = datetime.now(timezone.utc)
    weekly = []
    for i in range(7, -1, -1):
        end = now - timedelta(days=7 * i)
        start = end - timedelta(days=7)
        in_week = [r for r in records if start < _parse(r["completed_at"]) <= end]
        weekly.append(
            {
                "label": "This week" if i == 0 else f"{i}w ago",
                "sessions": len(in_week),
                "minutes": round(sum(r["duration_seconds"] for r in in_week) / 60, 1),
            }
        )

    return {
        "profile": {
            "email": profile["email"],
            "name": profile["name"],
            "registered_at": profile.get("registered_at"),
            "last_login": profile.get("last_login"),
        },
        "row": _student_row(profile, records, now),
        "summary": build_progress_summary(user_id, records),
        "score_history": [
            {"attempt": i + 1, "date": r["completed_at"], "score": r["score"], "title": r["title"]}
            for i, r in enumerate(records)
        ],
        "weekly_sessions": weekly,
        "settings": get_settings(user_id),
        "records": [
            {
                "id": r["id"],
                "exercise_id": r["exercise_id"],
                "expert": r.get("expert"),
                "measured_wpm": r.get("measured_wpm"),
                "target_wpm": r.get("target_wpm"),
                "score_breakdown": r.get("score_breakdown", []),
                "completed_at": r["completed_at"],
                "title": r["title"],
                "exercise_type": r["exercise_type"],
                "level": r.get("level"),
                "duration_seconds": r["duration_seconds"],
                "speaking_ratio": r.get("speaking_ratio"),
                "long_pauses": r.get("long_pauses", 0),
                "self_rating": r["self_rating"],
                "score": r["score"],
                "verdict": verdict(r["score"]),
            }
            for r in reversed(records)
        ],
    }
