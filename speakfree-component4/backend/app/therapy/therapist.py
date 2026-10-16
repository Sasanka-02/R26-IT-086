"""
Therapist portal — read-only views across all students.

Combines the account registry with each student's practice records to
give a therapist a caseload overview, a student list with plain-language
status, and per-student detail with chart-ready series.
"""

from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import LEVEL_LABELS, LEVELS, verdict
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.dashboard import build_progress_summary
from app.therapy.plan_review import reviews_for
from app.therapy.progress_store import all_records, get_records, normalize_user_id
from app.therapy.scoring import reviews_of
from app.therapy import appointments, messages, pilot
from app.therapy.exercises import get_exercise
from app.therapy.therapist_store import get_settings, homework_status
from app.therapy.user_store import age_group_of, get_user, list_users

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
        "age_group": summary["age_group"],
        "streak_days": summary["streak_days"],
        "status": _status(summary, records, now),
    }


ALERT_ORDER = ["high", "medium", "info"]
SCORE_DROPS = 3  # consecutive drops that raise an alert


def student_alerts(profile: dict, records: list[dict], now: datetime, unread_messages: int = 0) -> list[dict]:
    """Plain-sentence alerts for one student, e.g. "Kasun hasn't practised
    for 10 days" or "Nimali's score dropped 3 times in a row"."""
    first = (profile.get("name") or profile["email"]).split()[0]
    base = {"email": profile["email"], "name": profile.get("name") or profile["email"]}

    def alert(kind: str, severity: str, text: str, detail: str = "") -> dict:
        return {**base, "kind": kind, "severity": severity, "text": text, "detail": detail}

    out = []
    if unread_messages:
        out.append(alert("message", "info", f"New message from {first}",
                         f"{unread_messages} unread message{'s' if unread_messages != 1 else ''}."))
    if not records:
        registered = profile.get("registered_at")
        days = (now - _parse(registered)).days if registered else 0
        if days >= 3:
            out.append(alert("not_started", "medium", f"{first} hasn't started practising yet",
                             f"Registered {days} days ago."))
        return out

    days_idle = (now - _parse(records[-1]["completed_at"])).days
    if days_idle >= INACTIVE_DAYS:
        out.append(alert("inactive", "high", f"{first} hasn't practised for {days_idle} days",
                         "A short message or an easier assignment may help."))
    last = [r["score"] for r in records[-(SCORE_DROPS + 1):]]
    if len(last) == SCORE_DROPS + 1 and all(a > b for a, b in zip(last, last[1:])):
        out.append(alert("score_drop", "high", f"{first}'s score dropped {SCORE_DROPS} times in a row",
                         " → ".join(str(x) for x in last)))
    if len(records) >= 3 and all(r["self_rating"] == "hard" for r in records[-3:]):
        out.append(alert("hard", "medium", f"The last 3 exercises felt hard for {first}",
                         "Consider an easier plan or a lower level."))

    settings = get_settings(profile["email"])
    for item in homework_status(settings["assigned"], records):
        if item["overdue"]:
            ex = get_exercise(item["exercise_id"])
            title = ex.title if ex else item["exercise_id"]
            out.append(alert("homework_overdue", "medium", f"{first} hasn't finished “{title}”",
                             f"Due {item['due']} · done {item['done_count']} of {item['times']}."))
    return out


def list_students() -> list[dict]:
    now = datetime.now(timezone.utc)
    unread = messages.unread_for_therapists()
    rows = [{**_student_row(p, r, now), "unread_messages": unread.get(p["email"], 0)} for p, r in _students()]
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
    unread = messages.unread_for_therapists()
    alerts = []
    for profile, recs in students:
        alerts += student_alerts(profile, recs, now, unread.get(profile["email"], 0))
    alerts.sort(key=lambda a: ALERT_ORDER.index(a["severity"]))

    # Average improvement: first week vs last week for every student with
    # enough practice (the same rule as the pilot study).
    changes = [
        c["change"] for c in (pilot.participant(p["email"], r) for p, r in students if r) if c["included"]
    ]
    upcoming = appointments.for_therapist()
    next_week = now + timedelta(days=7)
    return {
        "alerts": alerts,
        "average_improvement": round(sum(changes) / len(changes), 1) if changes else None,
        "improvement_students": len(changes),
        "improving_students": sum(1 for c in changes if c > 0),
        "sessions_next_7_days": sum(
            1 for a in upcoming if a["student"] and datetime.fromisoformat(a["start"]) <= next_week
        ),
        "unread_messages": sum(unread.values()),
        "homework_overdue": sum(1 for a in alerts if a["kind"] == "homework_overdue"),
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
            "age": profile.get("age"),
            "age_group": age_group_of(user_id),
        },
        "row": _student_row(profile, records, now),
        "summary": build_progress_summary(user_id, records),
        "score_history": [
            {"attempt": i + 1, "date": r["completed_at"], "score": r["score"], "title": r["title"]}
            for i, r in enumerate(records)
        ],
        "weekly_sessions": weekly,
        "settings": get_settings(user_id),
        "homework": homework_status(get_settings(user_id)["assigned"], records),
        "alerts": student_alerts(profile, records, now),
        "plan": recommend_weekly_plan(records, get_settings(user_id), age_group=age_group_of(user_id)),
        "plan_reviews": list(reversed(reviews_for(user_id)))[:5],
        "records": [
            {
                "id": r["id"],
                "exercise_id": r["exercise_id"],
                "expert": r.get("expert"),
                "expert_reviews": reviews_of(r),
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
