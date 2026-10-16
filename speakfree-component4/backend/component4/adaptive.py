"""
Adaptive difficulty ladder (Beginner -> Intermediate -> Advanced) for the patient's focus.

★ COMPONENT 4 NOVELTY (adaptive learning) - the ladder is replayed from the patient's own
attempts, so it is deterministic, per-patient and needs no extra storage:

  * the starting rung comes from Component 3's severity level
      (Severe / Moderate -> Beginner, Mild -> Intermediate, Normal -> Advanced)
  * 2 strong attempts in a row at the current rung  -> move up
  * 2 difficult attempts in a row                    -> move back down
  * 2 strong attempts on Advanced                    -> family mastered -> re-screen suggested
  * the target speed of every passage adapts +/-10 % per strong / difficult attempt

Only attempts of the focus's ladder family (reading, clear_speech or sound_drill) made after
the current therapy profile was created are replayed - a new screening restarts the ladder at
its severity-based rung.
"""
from __future__ import annotations

from datetime import datetime

from .exercises import LEVELS
from .scoring import THRESHOLDS

LEVEL_LABELS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
STREAK_TO_MOVE = 2
PACE_STEP = 0.10
PACE_MIN, PACE_MAX = 0.7, 1.3


def is_strong(record: dict) -> bool:
    return record["score"] >= THRESHOLDS["strong"] and record["self_rating"] != "hard"


def is_weak(record: dict) -> bool:
    return record["score"] < THRESHOLDS["weak"] or record["self_rating"] == "hard"


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def level_state(records: list[dict], ladder_type: str, start_level: str = "beginner",
                since: str | None = None) -> dict:
    level = LEVELS.index(start_level) if start_level in LEVELS else 0
    since_dt = _parse(since) if since else None
    strong = weak = 0
    mastered = False
    scores: list[int] = []
    history: list[dict] = [{"at": since, "from": None, "to": LEVEL_LABELS[LEVELS[level]], "direction": "start",
                            "reason": "Starting level from the latest screening result."}]

    for r in records:
        if r.get("exercise_type") != ladder_type or r.get("level") not in LEVELS:
            continue
        if since_dt and _parse(r["completed_at"]) < since_dt:
            continue
        if LEVELS.index(r["level"]) != level:
            continue
        if is_strong(r):
            scores = (scores if strong else []) + [r["score"]]
            strong, weak = strong + 1, 0
        elif is_weak(r):
            scores = (scores if weak else []) + [r["score"]]
            strong, weak = 0, weak + 1
        else:
            strong = weak = 0

        if strong >= STREAK_TO_MOVE:
            if level < len(LEVELS) - 1:
                history.append({"at": r["completed_at"], "from": LEVEL_LABELS[LEVELS[level]],
                                "to": LEVEL_LABELS[LEVELS[level + 1]], "direction": "up",
                                "reason": f"{STREAK_TO_MOVE} strong attempts in a row (scores {', '.join(map(str, scores))})"})
                level, strong = level + 1, 0
            else:
                if not mastered:
                    history.append({"at": r["completed_at"], "from": LEVEL_LABELS[LEVELS[level]], "to": "Mastered",
                                    "direction": "mastered", "reason": "Final rung completed"})
                mastered, strong = True, STREAK_TO_MOVE
        elif weak >= STREAK_TO_MOVE and level > 0:
            history.append({"at": r["completed_at"], "from": LEVEL_LABELS[LEVELS[level]],
                            "to": LEVEL_LABELS[LEVELS[level - 1]], "direction": "down",
                            "reason": f"{STREAK_TO_MOVE} difficult attempts in a row (scores {', '.join(map(str, scores))})"})
            level, weak = level - 1, 0

    current = LEVELS[level]
    nxt = LEVELS[level + 1] if level + 1 < len(LEVELS) else None
    if mastered:
        progress_text = "You've completed the top level. A new screening will show how far you've come!"
    else:
        remaining = STREAK_TO_MOVE - strong
        progress_text = (f"{remaining} more strong attempt{'s' if remaining != 1 else ''} (score {THRESHOLDS['strong']}+) "
                         f"to {'unlock ' + LEVEL_LABELS[nxt] if nxt else 'complete the top level'}.")
    return {
        "level": current,
        "level_index": level,
        "label": LEVEL_LABELS[current],
        "next_level": nxt,
        "start_level": start_level,
        "strong_in_a_row": strong,
        "needed_to_advance": STREAK_TO_MOVE,
        "mastered": mastered,
        "progress_text": progress_text,
        "strong_threshold": THRESHOLDS["strong"],
        "weak_threshold": THRESHOLDS["weak"],
        "history": history,
    }


def level_change_message(before: dict, after: dict) -> str | None:
    if after["level_index"] > before["level_index"]:
        return f"Level up! You've unlocked {after['label']}."
    if after["level_index"] < before["level_index"]:
        return f"We've moved you back to {after['label']} for now so practice feels comfortable. You can work your way back up."
    if after["mastered"] and not before["mastered"]:
        return "Congratulations - you've completed the top level!"
    return None


def personal_target_wpm(base_wpm: int, exercise_id: str, records: list[dict]) -> int:
    factor = 1.0
    for r in records:
        if r["exercise_id"] != exercise_id:
            continue
        if is_strong(r):
            factor = min(PACE_MAX, factor + PACE_STEP)
        elif is_weak(r):
            factor = max(PACE_MIN, factor - PACE_STEP)
    return int(round(base_wpm * factor))


def attempt_feedback(attempt: dict) -> list[str]:
    """Plain-language observations about a single attempt."""
    notes: list[str] = []
    duration = attempt.get("duration_seconds") or 0
    ratio = attempt.get("speaking_ratio")
    if ratio is not None:
        if ratio >= 0.6:
            notes.append("You kept your voice going steadily for most of the exercise.")
        elif ratio < 0.35:
            notes.append("There was quite a lot of silence - next time try a gentle, continuous flow from word to word.")
        if attempt.get("long_pauses", 0):
            n = attempt["long_pauses"]
            notes.append(f"You took {n} long pause{'s' if n != 1 else ''}. Pausing is okay - try a slow breath and an easy start.")
        elif duration >= 15:
            notes.append("No long pauses - your speech flowed smoothly.")
        if attempt.get("quiet_warnings", 0) >= 2:
            notes.append("Your voice was quite soft at times - try a little more volume.")
        wpm, target = attempt.get("measured_wpm"), attempt.get("target_wpm")
        if wpm and target:
            if abs(wpm - target) <= 0.15 * target:
                notes.append(f"Your speed was about {wpm} words/min - right on the {target} target.")
            elif wpm > target:
                notes.append(f"You read at about {wpm} words/min, faster than the {target} target. Try slowing down.")
            else:
                notes.append(f"You read at about {wpm} words/min, a little slower than the {target} target - that's okay.")
    if attempt.get("exercise_type") == "sustained_vowel" and attempt.get("max_phonation_sec") is not None:
        notes.append(f"Your longest steady 'ahh' lasted {attempt['max_phonation_sec']:.1f} s "
                     f"(goal {attempt.get('target_seconds', 10)} s).")
    if attempt.get("exercise_type") == "sound_drill" and attempt.get("items_total"):
        notes.append(f"You marked {attempt.get('items_clear') or 0} of {attempt['items_total']} items as clear.")
    if duration < 15:
        notes.append("That was quite short - try practising for a bit longer next time.")
    if attempt.get("self_rating") == "easy":
        notes.append("You said this felt easy - a great sign you're ready for more challenge.")
    elif attempt.get("self_rating") == "hard":
        notes.append("You said this felt hard. We'll keep practising at a comfortable level.")
    return notes
