"""
Adaptive learning — scoring each attempt and moving the user through the
graded reading levels (beginner -> intermediate -> advanced/final stage).

Level rules (replayed from the user's own history, so they are fully
deterministic and per-user):
  * 2 strong readings in a row at the current level   -> move up a level
  * 2 difficult readings in a row at the current level -> move back down
  * 2 strong readings at the advanced level            -> final stage mastered

"Strong" and "difficult" use the thresholds calibrated against expert
ratings (see scoring.py). A therapist's level override restarts the replay
from the chosen level at the time of the override.
"""

from datetime import datetime

from app.therapy.schemas import SelfRating
from app.therapy.scoring import SHORT_ATTEMPT_SECONDS, score_with_breakdown, thresholds

LEVELS = ["beginner", "intermediate", "advanced"]
LEVEL_LABELS = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced (final stage)",
}

STREAK_TO_MOVE = 2

# Personal reading speed: each strong/weak attempt nudges the target by 10%,
# kept within 70–130% of the passage's base speed.
PACE_STEP = 0.10
PACE_MIN, PACE_MAX = 0.7, 1.3


def score_attempt(attempt: dict) -> tuple[int, list[dict]]:
    return score_with_breakdown(attempt)


def verdict(score: int) -> str:
    t = thresholds()
    if score >= max(80, t["strong"] + 5):
        return "Excellent"
    if score >= t["strong"] - 10:
        return "Good"
    if score >= t["weak"]:
        return "Getting there"
    return "A tough one — that's okay"


def attempt_feedback(attempt: dict) -> list[str]:
    """Plain-language observations about a single attempt."""
    notes: list[str] = []
    duration = attempt.get("duration_seconds") or 0
    ratio = attempt.get("speaking_ratio")
    long_pauses = attempt.get("long_pauses", 0)
    rating = attempt.get("self_rating", "ok")
    if ratio is not None:
        if ratio >= 0.6:
            notes.append("You kept your voice going steadily for most of the exercise.")
        elif ratio < 0.35:
            notes.append(
                "There was quite a lot of silence. That's fine — next time try a gentle, "
                "continuous flow from one word to the next."
            )
        else:
            notes.append("You spoke for a good part of the exercise.")
        if long_pauses == 0:
            notes.append("No long pauses — your speech flowed smoothly.")
        else:
            notes.append(
                f"You took {long_pauses} long pause{'s' if long_pauses != 1 else ''}. "
                "Pausing is okay; try a slow breath and an easy start on the next word."
            )
        if attempt.get("quiet_warnings", 0) >= 2:
            notes.append("Your voice was quite soft at times — try a little more volume.")
        wpm, target = attempt.get("measured_wpm"), attempt.get("target_wpm")
        if wpm and target:
            diff = wpm - target
            if abs(diff) <= 0.15 * target:
                notes.append(f"Your speed was about {wpm} words/min — right on the {target} target.")
            elif diff > 0:
                notes.append(f"You read at about {wpm} words/min, faster than the {target} target. Try slowing down.")
            else:
                notes.append(f"You read at about {wpm} words/min, a bit slower than the {target} target — that's okay.")
    elif duration >= SHORT_ATTEMPT_SECONDS:
        notes.append(f"You practised for {int(duration)} seconds — well done for completing it.")
    if duration < SHORT_ATTEMPT_SECONDS:
        notes.append("That was quite short — try speaking for a bit longer next time.")
    if rating == SelfRating.EASY.value:
        notes.append("You said this felt easy — great sign that you're ready for more challenge.")
    elif rating == SelfRating.HARD.value:
        notes.append("You said this felt hard. We'll keep practising at a comfortable level.")
    return notes


def _is_strong(record: dict, t: dict) -> bool:
    return record["score"] >= t["strong"] and record["self_rating"] != SelfRating.HARD.value


def _is_weak(record: dict, t: dict) -> bool:
    return record["score"] < t["weak"] or record["self_rating"] == SelfRating.HARD.value


def level_state(records: list[dict], override: dict | None = None) -> dict:
    """Replays the user's reading attempts to find their current level."""
    t = thresholds()
    level = 0
    since = None
    if override and override.get("level") in LEVELS:
        level = LEVELS.index(override["level"])
        since = datetime.fromisoformat(override["at"])
    strong = 0
    weak = 0
    mastered = False
    for record in records:
        if record.get("exercise_type") != "reading" or record.get("level") not in LEVELS:
            continue
        if since and datetime.fromisoformat(record["completed_at"]) < since:
            continue
        if LEVELS.index(record["level"]) != level:
            continue
        if _is_strong(record, t):
            strong, weak = strong + 1, 0
        elif _is_weak(record, t):
            strong, weak = 0, weak + 1
        else:
            strong, weak = 0, 0

        if strong >= STREAK_TO_MOVE:
            if level < len(LEVELS) - 1:
                level, strong = level + 1, 0
            else:
                mastered, strong = True, STREAK_TO_MOVE
        elif weak >= STREAK_TO_MOVE and level > 0:
            level, weak = level - 1, 0

    current = LEVELS[level]
    next_level = LEVELS[level + 1] if level + 1 < len(LEVELS) else None
    if mastered:
        progress_text = "You have completed the final reading stage. Keep it up to stay fluent!"
    else:
        remaining = STREAK_TO_MOVE - strong
        target = LEVEL_LABELS[next_level] if next_level else "complete the final stage"
        progress_text = (
            f"{remaining} more strong {LEVEL_LABELS[current]} reading"
            f"{'s' if remaining != 1 else ''} (score {t['strong']}+) to "
            f"{'unlock ' + target if next_level else target}."
        )
    return {
        "level": current,
        "level_index": level,
        "label": LEVEL_LABELS[current],
        "next_level": next_level,
        "next_label": LEVEL_LABELS[next_level] if next_level else None,
        "strong_in_a_row": strong,
        "needed_to_advance": STREAK_TO_MOVE,
        "mastered": mastered,
        "progress_text": progress_text,
        "set_by_therapist": bool(override and override.get("level")),
        "strong_threshold": t["strong"],
        "weak_threshold": t["weak"],
    }


def level_change_message(before: dict, after: dict) -> str | None:
    if after["level_index"] > before["level_index"]:
        return f"Level up! You've unlocked {after['label']} reading."
    if after["level_index"] < before["level_index"]:
        return (
            f"We've moved you back to {after['label']} reading for now, so practice "
            "feels comfortable again. You can work your way back up."
        )
    if after["mastered"] and not before["mastered"]:
        return "Congratulations — you've completed the final reading stage!"
    return None


def personal_target_wpm(base_wpm: int, exercise_id: str, records: list[dict]) -> int:
    """Adapts the reading speed to the student: strong attempts speed the
    highlight up 10%, difficult ones slow it down 10%."""
    t = thresholds()
    factor = 1.0
    for r in records:
        if r["exercise_id"] != exercise_id:
            continue
        if _is_strong(r, t):
            factor = min(PACE_MAX, factor + PACE_STEP)
        elif _is_weak(r, t):
            factor = max(PACE_MIN, factor - PACE_STEP)
    return int(round(base_wpm * factor))


BADGES = [
    ("first_step", "First step", "Completed your first exercise"),
    ("ten_sessions", "Committed", "Completed 10 exercises"),
    ("streak_3", "On a roll", "Practised 3 days in a row"),
    ("streak_7", "Week warrior", "Practised 7 days in a row"),
    ("score_90", "Top score", "Scored 90 or more"),
    ("intermediate", "Level up", "Unlocked Intermediate reading"),
    ("advanced", "Final stage", "Unlocked Advanced reading"),
    ("mastered", "Fluent reader", "Completed the final reading stage"),
    ("explorer", "Explorer", "Tried every type of exercise"),
]


def earned_badges(records: list[dict], level: dict, streak_days: int, best_streak: int) -> list[dict]:
    types = {r["exercise_type"] for r in records}
    earned = {
        "first_step": len(records) >= 1,
        "ten_sessions": len(records) >= 10,
        "streak_3": best_streak >= 3,
        "streak_7": best_streak >= 7,
        "score_90": any(r["score"] >= 90 for r in records),
        "intermediate": level["level_index"] >= 1,
        "advanced": level["level_index"] >= 2,
        "mastered": level["mastered"],
        "explorer": {"reading", "pacing", "daf", "picture"} <= types,
    }
    return [{"id": i, "title": t, "description": d, "earned": earned[i]} for i, t, d in BADGES]
