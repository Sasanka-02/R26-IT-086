"""
SO3 - Personalized Dashboard.

Builds a plain-language progress summary from the user's own practice
records: totals, streak, reading level, per-exercise breakdown, a
week-by-week table and recent attempts, plus a score history and daily
activity series for the progress charts.
"""

from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import earned_badges, level_state, verdict, word_level_state
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.therapist_store import get_settings, goal_progress

TYPE_LABELS = {
    "reading": "Reading practice",
    "pacing": "Pacing practice",
    "daf": "Delayed auditory feedback",
    "picture": "Picture description",
    "words": "Word practice",
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


def _daily(records: list[dict], today, days: int = 14) -> list[dict]:
    """Exercises and average score for each of the last `days` days, oldest first."""
    rows = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        on_day = [r for r in records if _parse(r["completed_at"]).date() == day]
        rows.append(
            {
                "date": day.isoformat(),
                "sessions": len(on_day),
                "average_score": _avg([r["score"] for r in on_day]),
            }
        )
    return rows


def _history(records: list[dict], limit: int = 30) -> list[dict]:
    """Every attempt's score in order (most recent `limit`), for the trend chart."""
    start = max(0, len(records) - limit)
    return [
        {
            "attempt": start + i + 1,
            "completed_at": r["completed_at"],
            "score": r["score"],
            "title": r["title"],
            "exercise_type": r["exercise_type"],
        }
        for i, r in enumerate(records[start:])
    ]


def _highlights(records: list[dict], level: dict, streak: int) -> list[str]:
    best = max(records, key=lambda r: r["score"])
    notes = [f"Your best result so far: {best['score']} in “{best['title']}”."]
    if streak >= 2:
        notes.append(f"You've practised {streak} days in a row — consistency really helps.")
    notes.append(f"Reading level: {level['label']}. {level['progress_text']}")
    words = word_level_state(records)
    if words["rounds"]:
        notes.append(f"Word practice: {words['progress_text']}")
    pauses = [r["long_pauses"] for r in records[-5:] if r.get("speaking_ratio") is not None]
    if pauses and sum(pauses) / len(pauses) >= 1:
        notes.append("Long pauses show up often lately — try a slow breath before each sentence.")
    hard = sum(1 for r in records[-5:] if r["self_rating"] == "hard")
    if hard >= 2:
        notes.append("Several recent exercises felt hard. It's fine to repeat easier ones for a while.")
    return notes


REPORT_STATUS = {
    "improving": "Improving",
    "steady": "Steady",
    "needs_support": "Needs support",
}


def _report_card(records: list[dict], level: dict, settings: dict, now: datetime) -> dict:
    """The progress page's first card: one sentence, a traffic light, what
    happened this week and the next step — no charts needed to read it."""
    plan = recommend_weekly_plan(records, settings)
    first = plan["exercises"][0] if plan["exercises"] else None
    next_step = f"Next: {first['title']}. {first['explanation']}" if first else "Next: pick any exercise to start."
    if not records:
        return {
            "status": "steady",
            "label": "Getting started",
            "headline": "No exercises saved yet — your report starts with your first exercise.",
            "this_week": "Nothing practised yet this week.",
            "next_step": next_step,
            "reasons": [],
        }

    week_ago = now - timedelta(days=7)
    this_week = [r for r in records if _parse(r["completed_at"]) > week_ago]
    last_week = [r for r in records if week_ago - timedelta(days=7) < _parse(r["completed_at"]) <= week_ago]
    trend = _trend(records)
    recent_moves = [h for h in level["history"] if _parse(h["at"]) > now - timedelta(days=14)]
    hard = sum(1 for r in records[-5:] if r["self_rating"] == "hard")
    days_since = (now - _parse(records[-1]["completed_at"])).days

    support: list[str] = []
    if days_since >= 7:
        support.append(f"No practice for {days_since} days.")
    if trend["label"] == "Dipped a little":
        support.append(trend["detail"])
    if hard >= 2:
        support.append(f"{hard} of the last 5 exercises felt hard.")
    if any(h["direction"] == "down" for h in recent_moves):
        support.append("Reading level was moved down recently to keep practice comfortable.")
    gains: list[str] = []
    if trend["label"] == "Improving":
        gains.append(trend["detail"])
    for h in recent_moves:
        if h["direction"] == "up":
            gains.append(f"Moved from {h['from']} to {h['to']} {h['reason']}.")
        elif h["direction"] == "mastered":
            gains.append(f"Completed the final reading stage {h['reason']}.")

    if support:
        status = "needs_support"
        if days_since >= 7 and len(support) == 1:
            headline = f"It's been {days_since} days since your last exercise — a short session this week will get you going again."
        else:
            headline = "This has been a harder patch — practice will stay at a comfortable level for now."
    elif gains:
        status = "improving"
        headline = f"You're improving — your recent scores average {_avg([r['score'] for r in records[-3:]])}."
    else:
        status = "steady"
        headline = f"You're holding steady at about {_avg([r['score'] for r in records[-3:]])} out of 100."
    if len(records) < 4 and not support:
        headline = "A good start — a few more exercises will show which way your scores are going."

    if this_week:
        avg = _avg([r["score"] for r in this_week])
        minutes = round(sum(r["duration_seconds"] for r in this_week) / 60)
        week_text = (
            f"This week you did {len(this_week)} exercise{'s' if len(this_week) != 1 else ''} "
            f"({minutes} min) with an average score of {avg}"
        )
        if last_week:
            before = _avg([r["score"] for r in last_week])
            change = "up from" if avg > before else ("down from" if avg < before else "the same as")
            week_text += f", {change} {before} last week"
        week_text += "."
    else:
        week_text = f"You haven't practised this week yet — your last exercise was {days_since} days ago."

    return {
        "status": status,
        "label": REPORT_STATUS[status],
        "headline": headline,
        "this_week": week_text,
        "next_step": next_step,
        "reasons": support or gains,
    }


def build_progress_summary(user_id: str, records: list[dict]) -> dict:
    settings = get_settings(user_id)
    level = level_state(records, settings["level_override"])
    goals = goal_progress(settings["goals"], records)
    now = datetime.now(timezone.utc)
    report_card = _report_card(records, level, settings, now)
    word_level = word_level_state(records)
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
            "daily": [],
            "history": [],
            "recent": [],
            "highlights": [],
            "badges": earned_badges(records, level, 0, 0),
            "goals": goals,
            "first_vs_latest": [],
            "report_card": report_card,
            "word_level": word_level,
        }

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
        "daily": _daily(records, now.date()),
        "history": _history(records),
        "recent": recent,
        "highlights": _highlights(records, level, streak),
        "badges": earned_badges(records, level, streak, _best_streak(records)),
        "goals": goals,
        "first_vs_latest": _first_vs_latest(records),
        "report_card": report_card,
        "word_level": word_level,
    }
