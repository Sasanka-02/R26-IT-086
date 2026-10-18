"""
Patient dashboard - a plain-language view of the patient's own practice, built from the plan.

  report_card      the first card on the progress page: a traffic light (improving / steady /
                   needs support), one headline sentence, "this week" and the next step - readable
                   without any chart
  highlights       short "what this means for you" notes
  badges           milestones earned by practising (kid-friendly titles for ages 6-11)
  weekly           exercises, minutes and average score for the last 4 weeks
  first_vs_latest  first attempt (baseline) against the latest attempt, per exercise
  why              why today's plan was chosen, in words (the adaptive context explained)

Patient-safe: no screening category or level is ever named here.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .progress import best_streak, first_vs_latest, parse, trend, weekly

REPORT_LABELS = {"improving": "Improving", "steady": "Steady", "needs_support": "Needs support"}

BADGES = [
    ("first_step", "First step", "Completed your first exercise"),
    ("ten_sessions", "Committed", "Completed 10 exercises"),
    ("streak_3", "On a roll", "Practised 3 days in a row"),
    ("streak_7", "Week warrior", "Practised 7 days in a row"),
    ("score_90", "Top score", "Scored 90 or more"),
    ("level_up", "Level up", "Moved up a practice level"),
    ("top_level", "Champion", "Completed the top level of a ladder"),
    ("explorer", "Explorer", "Tried every type of exercise in your plan"),
    ("first_words", "First words", "Finished your first word round"),
    ("word_master", "Word master", "Finished all 7 word levels"),
]
KID_TITLES = {
    "first_step": "Super Speaker ⭐", "ten_sessions": "Practice Hero 🦸", "streak_3": "Three in a Row 🔥",
    "streak_7": "Super Week 🌈", "score_90": "Shining Star 🌟", "level_up": "Level Up! 🚀",
    "top_level": "Speaking Champion 🏆", "explorer": "Explorer 🧭", "first_words": "First Words 🐣",
    "word_master": "Word Wizard 🪄",
}
WORD_BADGES = ("first_words", "word_master")


def _avg(values: list[float]) -> int | None:
    return int(round(sum(values) / len(values))) if values else None


def highlights(records: list[dict], level: dict, words: dict | None, streak: int) -> list[str]:
    if not records:
        return []
    best = max(records, key=lambda r: r["score"])
    notes = [f"Your best result so far: {best['score']} in “{best['title']}”."]
    if streak >= 2:
        notes.append(f"You've practised {streak} days in a row - consistency really helps.")
    notes.append(f"Your level: {level['label']}. {level['progress_text']}")
    if words and words["rounds"]:
        notes.append(f"Word practice: {words['progress_text']}")
    live = [r for r in records[-5:] if r.get("speaking_ratio") is not None]
    if live and sum(r.get("long_pauses", 0) for r in live) / len(live) >= 1:
        notes.append("Long pauses show up often lately - try a slow breath before each sentence.")
    if sum(1 for r in records[-5:] if r["self_rating"] == "hard") >= 2:
        notes.append("Several recent exercises felt hard. It's fine to repeat easier ones for a while.")
    return notes


def badges(records: list[dict], level: dict, skill: dict | None, words: dict | None,
           plan_types: set[str], playful: bool) -> list[dict]:
    types = {r["exercise_type"] for r in records}
    histories = level["history"] + (skill["history"] if skill else []) + (words["history"] if words else [])
    earned = {
        "first_step": len(records) >= 1,
        "ten_sessions": len(records) >= 10,
        "streak_3": best_streak(records) >= 3,
        "streak_7": best_streak(records) >= 7,
        "score_90": any(r["score"] >= 90 for r in records),
        "level_up": any(h["direction"] == "up" for h in histories),
        "top_level": level["mastered"] or bool(skill and skill["mastered"]) or bool(words and words["mastered"]),
        "explorer": bool(plan_types) and plan_types <= types,
        "first_words": "words" in types,
        "word_master": bool(words and words["level"] > words["word_levels"]),
    }
    return [
        {"id": key, "title": KID_TITLES[key] if playful else title, "description": desc, "earned": earned[key]}
        for key, title, desc in BADGES
        if words is not None or key not in WORD_BADGES
    ]


def report_card(records: list[dict], level: dict, next_ex: dict | None, now: datetime) -> dict:
    next_step = (f"{next_ex['title']}. {next_ex.get('reason') or ''}".strip() if next_ex
                 else "Pick any exercise to start.")
    if not records:
        return {"status": "steady", "label": "Getting started",
                "headline": "No exercises saved yet - your report starts with your first exercise.",
                "this_week": "Nothing practised yet this week.", "next_step": next_step, "reasons": []}

    week_ago = now - timedelta(days=7)
    this_week = [r for r in records if parse(r["completed_at"]) > week_ago]
    last_week = [r for r in records if week_ago - timedelta(days=7) < parse(r["completed_at"]) <= week_ago]
    t = trend(records)
    recent_moves = [h for h in level["history"] if h.get("at") and parse(h["at"]) > now - timedelta(days=14)]
    hard = sum(1 for r in records[-5:] if r["self_rating"] == "hard")
    days_since = (now - parse(records[-1]["completed_at"])).days

    support: list[str] = []
    if days_since >= 7:
        support.append(f"No practice for {days_since} days.")
    if t["label"] == "Dipped a little":
        support.append(t["detail"])
    if hard >= 2:
        support.append(f"{hard} of the last 5 exercises felt hard.")
    if any(h["direction"] == "down" for h in recent_moves):
        support.append("Your practice level was moved down recently to keep practice comfortable.")
    gains: list[str] = []
    if t["label"] == "Improving":
        gains.append(t["detail"])
    for h in recent_moves:
        if h["direction"] == "up":
            gains.append(f"Moved from {h['from']} to {h['to']} after {h['reason']}.")
        elif h["direction"] == "mastered":
            gains.append(f"Completed {h['from']} - {h['reason'].lower()}.")

    recent_avg = _avg([r["score"] for r in records[-3:]])
    if support:
        status = "needs_support"
        headline = (f"It's been {days_since} days since your last exercise - a short session this week will get you going again."
                    if days_since >= 7 and len(support) == 1
                    else "This has been a harder patch - practice will stay at a comfortable level for now.")
    elif gains:
        status = "improving"
        headline = f"You're improving - your recent scores average {recent_avg}."
    else:
        status = "steady"
        headline = f"You're holding steady at about {recent_avg} out of 100."
    if len(records) < 4 and not support:
        headline = "A good start - a few more exercises will show which way your scores are going."

    if this_week:
        avg = _avg([r["score"] for r in this_week]) or 0  # this_week is non-empty here
        minutes = round(sum(r.get("duration_seconds") or 0 for r in this_week) / 60)
        week_text = (f"This week you did {len(this_week)} exercise{'s' if len(this_week) != 1 else ''} "
                     f"({minutes} min) with an average score of {avg}")
        if last_week:
            before = _avg([r["score"] for r in last_week]) or 0  # last_week is non-empty here
            change = "up from" if avg > before else ("down from" if avg < before else "the same as")
            week_text += f", {change} {before} last week"
        week_text += "."
    else:
        week_text = f"You haven't practised this week yet - your last exercise was {days_since} days ago."
    return {"status": status, "label": REPORT_LABELS[status], "headline": headline, "this_week": week_text,
            "next_step": next_step, "reasons": support or gains}


def confidence_label(exploration_bonus: float | None) -> str | None:
    """The bandit's uncertainty α√(xᵀA⁻¹x) on the score scale, as a plain confidence level."""
    if exploration_bonus is None:
        return None
    u = exploration_bonus * 100
    return "low" if u > 60 else "medium" if u > 30 else "high"


def explain_plan(context: list[float], level: dict, focus_name: str, assigned: int, records: list[dict]) -> list[str]:
    """Why this plan, in words - built from the same context vector the bandit used."""
    _, _, avg, trend_v, comfort, *_ = context
    recent = records[-5:]
    lines = [f"You're practising at {level['label']} ({level['ages']} tasks). {level['progress_text']}",
             f"Your plan focus: “{focus_name}” - the extra practice is chosen to help with it."]
    if recent:
        lines.append(f"Your recent average score is {round(avg * 100)} over your last {len(recent)} exercise"
                     f"{'s' if len(recent) != 1 else ''}.")
        if len(records) >= 4:
            direction = "going up" if trend_v > 0.02 else "dipping a little" if trend_v < -0.02 else "steady"
            lines.append(f"Your scores are {direction}, so the plan {'adds a little challenge' if direction == 'going up' else 'keeps practice comfortable' if direction != 'steady' else 'keeps a similar mix'}.")
        not_hard = round(comfort * len(recent))
        lines.append(f"{not_hard} of your last {len(recent)} exercises didn't feel hard.")
    else:
        lines.append("No exercises yet - your first plan comes from your screening and your age.")
    if assigned:
        lines.append(f"Your therapist assigned {assigned} exercise{'s' if assigned != 1 else ''} - they always come first.")
    lines.append("Exercises you haven't tried yet are mixed in so the plan can learn what suits you.")
    return lines


def build_dashboard(records: list[dict], level: dict, skill: dict | None, words: dict | None,
                    today: list[dict], plan_types: set[str], playful: bool, streak: int, now: datetime) -> dict:
    return {
        "report_card": report_card(records, level, today[0] if today else None, now),
        "highlights": highlights(records, level, words, streak),
        "badges": badges(records, level, skill, words, plan_types, playful),
        "weekly": weekly(records, now),
        "active_days": len({parse(r["completed_at"]).date() for r in records}),
        "best_streak": best_streak(records),
        "first_vs_latest": first_vs_latest(records),
    }
