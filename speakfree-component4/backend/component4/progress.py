"""Progress summary built from a patient's own therapy attempts (dashboard + assistant)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .scoring import verdict

TYPE_LABELS = {
    "reading": "Reading practice",
    "pacing": "Pacing practice",
    "daf": "Delayed auditory feedback",
    "picture": "Picture description",
    "clear_speech": "Clear speech",
    "loudness": "Loud & clear voice",
    "sustained_vowel": "Breath support",
    "sound_drill": "Sound practice",
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
    last3 = _avg([r["score"] for r in records[-3:]])
    prev3 = _avg([r["score"] for r in records[-6:-3]])
    diff = last3 - prev3
    if diff >= 5:
        return {"label": "Improving", "delta": diff, "detail": f"Your last 3 scores average {last3}, up {diff} points."}
    if diff <= -5:
        return {"label": "Dipped a little", "delta": diff,
                "detail": f"Your last 3 scores average {last3}, down {-diff} points. Ups and downs are normal."}
    return {"label": "Steady", "delta": diff, "detail": f"Your recent scores are consistent, around {last3}."}


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
        "trend": trend(records),
        "by_type": [
            {"type": t, "label": TYPE_LABELS.get(t, t.title()), "attempts": len(rs),
             "average_score": _avg([r["score"] for r in rs]), "best_score": max(r["score"] for r in rs)}
            for t, rs in by_type.items()
        ],
        "recent": [
            {"exercise_id": r["exercise_id"], "title": r["title"], "score": r["score"], "verdict": verdict(r["score"]),
             "completed_at": r["completed_at"], "self_rating": r["self_rating"], "exercise_type": r["exercise_type"]}
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
