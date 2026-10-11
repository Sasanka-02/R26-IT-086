"""
SO3 - Personalized Dashboard.

Builds a plain-language progress summary from the user's own practice
records: totals, streak, reading level, per-exercise breakdown, a
week-by-week table and recent attempts. Designed to be read as text and
tables rather than charts.
"""

from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import earned_badges, level_state, verdict
from app.therapy.therapist_store import get_settings, goal_progress

TYPE_LABELS = {
    "reading": "Reading practice",
    "pacing": "Pacing practice",
    "daf": "Delayed auditory feedback",
    "picture": "Picture description",
}


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _avg(values: list[float]) -> int | None:
    return int(round(sum(values) / len(values))) if values else None


def _streak_days(records: list[dict], today) -> int:
    days = {_parse(r["completed_at"]).date() for r in records}
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _best_streak(records: list[dict]) -> int:
    days = sorted({_parse(r["completed_at"]).date() for r in records})
    best = run = 0
    for i, day in enumerate(days):
        run = run + 1 if i and (day - days[i - 1]).days == 1 else 1
        best = max(best, run)
    return best


def _first_vs_latest(records: list[dict]) -> list[dict]:
    """Baseline (first attempt) against the latest attempt, per exercise."""
    rows = []
    seen: dict[str, list[dict]] = {}
    for r in records:
        seen.setdefault(r["exercise_id"], []).append(r)
    for attempts in seen.values():
        if len(attempts) < 2:
            continue
        first, last = attempts[0], attempts[-1]
        rows.append(
            {
                "exercise_id": first["exercise_id"],
                "title": first["title"],
                "attempts": len(attempts),
                "first_score": first["score"],
                "latest_score": last["score"],
                "change": last["score"] - first["score"],
                "first_pauses": first.get("long_pauses") if first.get("speaking_ratio") is not None else None,
                "latest_pauses": last.get("long_pauses") if last.get("speaking_ratio") is not None else None,
            }
        )
    return rows


def _trend(records: list[dict]) -> dict:
    if len(records) < 4:
        return {
            "label": "Just getting started",
            "detail": "Complete a few more exercises to see whether your scores are improving.",
        }
    last3 = _avg([r["score"] for r in records[-3:]])
    prev3 = _avg([r["score"] for r in records[-6:-3]])
    diff = last3 - prev3
    if diff >= 5:
        return {"label": "Improving", "detail": f"Your last 3 scores average {last3}, up {diff} points from before."}
    if diff <= -5:
        return {
            "label": "Dipped a little",
            "detail": f"Your last 3 scores average {last3}, down {-diff} points. Ups and downs are normal.",
        }
    return {"label": "Steady", "detail": f"Your recent scores are consistent, averaging about {last3}."}


def _weekly(records: list[dict], now: datetime, weeks: int = 4) -> list[dict]:
    labels = ["This week", "Last week", "2 weeks ago", "3 weeks ago"]
    rows = []
    for i in range(weeks):
        end = now - timedelta(days=7 * i)
        start = end - timedelta(days=7)
        in_week = [r for r in records if start < _parse(r["completed_at"]) <= end]
        rows.append(
            {
                "label": labels[i] if i < len(labels) else f"{i} weeks ago",
                "sessions": len(in_week),
                "minutes": round(sum(r["duration_seconds"] for r in in_week) / 60, 1),
                "average_score": _avg([r["score"] for r in in_week]),
            }
        )
    return rows


def _highlights(records: list[dict], level: dict, streak: int) -> list[str]:
    best = max(records, key=lambda r: r["score"])
    notes = [f"Your best result so far: {best['score']} in “{best['title']}”."]
    if streak >= 2:
        notes.append(f"You've practised {streak} days in a row — consistency really helps.")
    notes.append(f"Reading level: {level['label']}. {level['progress_text']}")
    pauses = [r["long_pauses"] for r in records[-5:] if r.get("speaking_ratio") is not None]
    if pauses and sum(pauses) / len(pauses) >= 1:
        notes.append("Long pauses show up often lately — try a slow breath before each sentence.")
    hard = sum(1 for r in records[-5:] if r["self_rating"] == "hard")
    if hard >= 2:
        notes.append("Several recent exercises felt hard. It's fine to repeat easier ones for a while.")
    return notes


def build_progress_summary(user_id: str, records: list[dict]) -> dict:
    settings = get_settings(user_id)
    level = level_state(records, settings["level_override"])
    goals = goal_progress(settings["goals"], records)
    if not records:
        return {
            "user_id": user_id,
            "has_data": False,
            "level": level,
            "total_sessions": 0,
            "total_minutes": 0,
            "active_days": 0,
            "streak_days": 0,
            "average_score": None,
            "best_score": None,
            "trend": _trend(records),
            "by_type": [],
            "weekly": [],
            "recent": [],
            "highlights": [],
            "badges": earned_badges(records, level, 0, 0),
            "goals": goals,
            "first_vs_latest": [],
        }

    now = datetime.now(timezone.utc)
    streak = _streak_days(records, now.date())

    by_type = []
    for type_key, label in TYPE_LABELS.items():
        items = [r for r in records if r["exercise_type"] == type_key]
        if not items:
            continue
        by_type.append(
            {
                "type": type_key,
                "label": label,
                "sessions": len(items),
                "average_score": _avg([r["score"] for r in items]),
                "best_score": max(r["score"] for r in items),
                "last_done": items[-1]["completed_at"],
            }
        )

    recent = [
        {
            "id": r["id"],
            "title": r["title"],
            "exercise_type": r["exercise_type"],
            "completed_at": r["completed_at"],
            "score": r["score"],
            "verdict": verdict(r["score"]),
            "self_rating": r["self_rating"],
            "duration_seconds": r["duration_seconds"],
        }
        for r in reversed(records[-8:])
    ]

    return {
        "user_id": user_id,
        "has_data": True,
        "level": level,
        "total_sessions": len(records),
        "total_minutes": round(sum(r["duration_seconds"] for r in records) / 60, 1),
        "active_days": len({_parse(r["completed_at"]).date() for r in records}),
        "streak_days": streak,
        "average_score": _avg([r["score"] for r in records]),
        "best_score": max(r["score"] for r in records),
        "trend": _trend(records),
        "by_type": by_type,
        "weekly": _weekly(records, now),
        "recent": recent,
        "highlights": _highlights(records, level, streak),
        "badges": earned_badges(records, level, streak, _best_streak(records)),
        "goals": goals,
        "first_vs_latest": _first_vs_latest(records),
    }
