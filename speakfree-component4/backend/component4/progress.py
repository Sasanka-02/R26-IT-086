"""Progress summary built from a patient's own therapy attempts (dashboard + assistant)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .scoring import verdict

TYPE_LABELS = {
    "reading": "Reading practice",
    "pacing": "Pacing practice",
    "daf": "Delayed auditory feedback",
    "picture": "Picture description",
    "conversation": "Conversation practice",
    "clear_speech": "Clear speech",
    "loudness": "Loud & clear voice",
    "sustained_vowel": "Breath support",
    "sound_drill": "Sound practice",
    "words": "Word practice",
    "roleplay": "Role-plays & talks",
}


def parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _avg(values: list[float]) -> int | None:
    return int(round(sum(values) / len(values))) if values else None


def streak_days(records: list[dict], today: date) -> int:
    days = {parse(r["completed_at"]).date() for r in records}
    day = today if today in days else today - timedelta(days=1)
    n = 0
    while day in days:
        n += 1
        day -= timedelta(days=1)
    return n


def trend(records: list[dict]) -> dict:
    if len(records) < 4:
        return {"label": "Just getting started", "delta": 0,
                "detail": "Complete a few more exercises to see whether your scores are improving."}
    # 4+ records -> both windows are non-empty, so neither average is None
    last3 = _avg([r["score"] for r in records[-3:]]) or 0
    prev3 = _avg([r["score"] for r in records[-6:-3]]) or 0
    diff = last3 - prev3
    if diff >= 5:
        return {"label": "Improving", "delta": diff, "detail": f"Your last 3 scores average {last3}, up {diff} points."}
    if diff <= -5:
        return {"label": "Dipped a little", "delta": diff,
                "detail": f"Your last 3 scores average {last3}, down {-diff} points. Ups and downs are normal."}
    return {"label": "Steady", "delta": diff, "detail": f"Your recent scores are consistent, around {last3}."}


def best_streak(records: list[dict]) -> int:
    days = sorted({parse(r["completed_at"]).date() for r in records})
    best = run = 0
    for i, day in enumerate(days):
        run = run + 1 if i and (day - days[i - 1]).days == 1 else 1
        best = max(best, run)
    return best


def weekly(records: list[dict], now: datetime, weeks: int = 4) -> list[dict]:
    """Rolling 7-day windows, newest first (weekly practice chart + week-by-week table)."""
    labels = ["This week", "Last week", "2 weeks ago", "3 weeks ago"]
    rows = []
    for i in range(weeks):
        end = now - timedelta(days=7 * i)
        start = end - timedelta(days=7)
        in_week = [r for r in records if start < parse(r["completed_at"]) <= end]
        rows.append({
            "label": labels[i] if i < len(labels) else f"{i} weeks ago",
            "sessions": len(in_week),
            "minutes": round(sum(r.get("duration_seconds") or 0 for r in in_week) / 60, 1),
            "average_score": _avg([r["score"] for r in in_week]),
        })
    return rows


def first_vs_latest(records: list[dict]) -> list[dict]:
    """First attempt (baseline) against the latest attempt, per exercise tried at least twice."""
    seen: dict[str, list[dict]] = {}
    for r in records:
        seen.setdefault(r["exercise_id"], []).append(r)
    rows = [{"exercise_id": a[0]["exercise_id"], "title": a[-1]["title"], "attempts": len(a),
             "first_score": a[0]["score"], "latest_score": a[-1]["score"], "change": a[-1]["score"] - a[0]["score"]}
            for a in seen.values() if len(a) >= 2]
    return sorted(rows, key=lambda r: r["attempts"], reverse=True)


def summary(records: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    by_type: dict[str, list[dict]] = {}
    for r in records:
        by_type.setdefault(r["exercise_type"], []).append(r)
    return {
        "has_data": bool(records),
        "total_sessions": len(records),
        "total_minutes": round(sum(r.get("duration_seconds") or 0 for r in records) / 60, 1),
        "average_score": _avg([r["score"] for r in records]),
        "best_score": max((r["score"] for r in records), default=None),
        "streak_days": streak_days(records, today),
        "best_streak": best_streak(records),
        "active_days": len({parse(r["completed_at"]).date() for r in records}),
        "trend": trend(records),
        "weekly": weekly(records, now),
        "first_vs_latest": first_vs_latest(records),
        "by_type": [
            {"type": t, "label": TYPE_LABELS.get(t, t.title()), "attempts": len(rs),
             "average_score": _avg([r["score"] for r in rs]), "best_score": max(r["score"] for r in rs)}
            for t, rs in by_type.items()
        ],
        "recent": [
            {"exercise_id": r["exercise_id"], "title": r["title"], "score": r["score"], "verdict": verdict(r["score"]),
             "completed_at": r["completed_at"], "self_rating": r["self_rating"], "exercise_type": r["exercise_type"],
             "duration_seconds": r.get("duration_seconds") or 0}
            for r in reversed(records[-8:])
        ],
        "history": [
            {"attempt": i + 1, "score": r["score"], "completed_at": r["completed_at"], "title": r["title"],
             "exercise_type": r["exercise_type"]}
            for i, r in enumerate(records)
        ][-40:],
        "daily": [
            {"date": (today - timedelta(days=i)).isoformat(),
             "sessions": sum(1 for r in records if parse(r["completed_at"]).date() == today - timedelta(days=i)),
             "average_score": _avg([r["score"] for r in records if parse(r["completed_at"]).date() == today - timedelta(days=i)])}
            for i in range(13, -1, -1)
        ],
    }
