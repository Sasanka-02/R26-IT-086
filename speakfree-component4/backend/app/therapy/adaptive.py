"""
Adaptive learning — scoring each attempt and moving the user through the
graded reading levels (beginner -> intermediate -> advanced/final stage).

Level rules (replayed from the user's own history, so they are fully
deterministic and per-user):
  * 1 strong reading at the current level             -> move up a level
  * 2 difficult readings in a row at the current level -> move back down
  * 1 strong reading at the advanced level             -> final stage mastered

Children also have a word ladder (word_level_state): word levels 1–7 then
three phrase stages, with the same 1-up / 2-down rule and separate state.

"Strong" and "difficult" use the thresholds calibrated against expert
ratings (see scoring.py). A therapist's level override restarts the replay
from the chosen level at the time of the override.
"""

from datetime import datetime

from app.therapy.exercises import (
    PACE_RANGE,
    WORD_LADDER_IDS,
    WORD_LADDER_SIZE,
    WORD_LEVEL_COUNT,
    exercises_for,
    get_exercise,
    word_stage_label,
)
from app.therapy.user_store import DEFAULT_AGE_GROUP
from app.therapy.schemas import SelfRating
from app.therapy.scoring import SHORT_ATTEMPT_SECONDS, score_with_breakdown, thresholds

LEVELS = ["beginner", "intermediate", "advanced"]
LEVEL_LABELS = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced (final stage)",
}

# One strong attempt unlocks the next level; two difficult ones in a row are
# needed to step back, so a single bad day never moves a student down.
STRONG_TO_MOVE_UP = 1
HARD_TO_MOVE_DOWN = 2


def _streak_reason(count: int, kind: str, noun: str, scores: list[int]) -> str:
    """'after 1 strong Beginner reading (score 82)' or
    'after 2 difficult Beginner readings in a row (scores 30, 35)'."""
    if count == 1:
        return f"after 1 {kind} {noun} (score {scores[-1]})"
    return f"after {count} {kind} {noun}s in a row (scores {', '.join(str(x) for x in scores[-count:])})"

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
    if attempt.get("exercise_type") == "words":
        correct, total = attempt.get("words_correct"), attempt.get("words_total")
        if correct is not None and total:
            if correct == total:
                notes.append(f"You said all {total} words well — superstar! ⭐")
            elif correct >= 0.75 * total:
                notes.append(f"You said {correct} of {total} words well. Great work!")
            else:
                notes.append(
                    f"You said {correct} of {total} words well. Tricky words get easier each time — "
                    "try the 🔊 Listen button first and say them slowly."
                )
        else:
            notes.append("Well done for finishing the word round!")
        if rating == SelfRating.HARD.value:
            notes.append("That felt hard. We'll keep practising at this level until it feels easier.")
        return notes
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


def _ladder_rung(record: dict, age_group: str) -> int | None:
    """The level index of a record's exercise on this age group's ladder, or
    None if the exercise isn't on that ladder. Each age group has its own
    Beginner -> Intermediate -> Advanced ladder, so levels are tracked per group."""
    ex = get_exercise(record.get("exercise_id", ""))
    if ex is None or ex.level is None or age_group not in ex.age_groups:
        return None
    return LEVELS.index(ex.level.value)


def level_state(
    records: list[dict], override: dict | None = None, age_group: str = DEFAULT_AGE_GROUP
) -> dict:
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
    streak_scores: list[int] = []
    history: list[dict] = []
    if since:
        history.append(
            {"at": override["at"], "from": None, "to": LEVEL_LABELS[LEVELS[level]],
             "direction": "therapist", "reason": override.get("note") or "Level set by the therapist."}
        )

    def move(record: dict, new_level: int | None, direction: str, kind: str, count: int) -> None:
        history.append(
            {
                "at": record["completed_at"],
                "from": LEVEL_LABELS[LEVELS[level]],
                "to": LEVEL_LABELS[LEVELS[new_level]] if new_level is not None else "Final stage completed",
                "direction": direction,
                "reason": _streak_reason(count, kind, f"{LEVEL_LABELS[LEVELS[level]]} exercise", streak_scores),
            }
        )

    for record in records:
        rung = _ladder_rung(record, age_group)
        if rung is None:
            continue
        if since and datetime.fromisoformat(record["completed_at"]) < since:
            continue
        if rung != level:
            continue
        if _is_strong(record, t):
            streak_scores = (streak_scores if strong else []) + [record["score"]]
            strong, weak = strong + 1, 0
        elif _is_weak(record, t):
            streak_scores = (streak_scores if weak else []) + [record["score"]]
            strong, weak = 0, weak + 1
        else:
            strong, weak = 0, 0

        if strong >= STRONG_TO_MOVE_UP:
            if level < len(LEVELS) - 1:
                move(record, level + 1, "up", "strong", STRONG_TO_MOVE_UP)
                level, strong = level + 1, 0
            else:
                if not mastered:
                    move(record, None, "mastered", "strong", STRONG_TO_MOVE_UP)
                mastered, strong = True, STRONG_TO_MOVE_UP
        elif weak >= HARD_TO_MOVE_DOWN and level > 0:
            move(record, level - 1, "down", "difficult", HARD_TO_MOVE_DOWN)
            level, weak = level - 1, 0

    current = LEVELS[level]
    next_level = LEVELS[level + 1] if level + 1 < len(LEVELS) else None
    if mastered:
        progress_text = "You have completed the final stage. Keep practising to stay fluent!"
    else:
        remaining = STRONG_TO_MOVE_UP - strong
        target = LEVEL_LABELS[next_level] if next_level else "complete the final stage"
        progress_text = (
            f"{remaining} more strong {LEVEL_LABELS[current]} exercise"
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
        "needed_to_advance": STRONG_TO_MOVE_UP,
        "mastered": mastered,
        "progress_text": progress_text,
        "set_by_therapist": bool(
            override and override.get("level") and not override.get("by", "").startswith("screening")
        ),
        "strong_threshold": t["strong"],
        "weak_threshold": t["weak"],
        "history": history,
        "age_group": age_group,
    }


def word_level_state(records: list[dict]) -> dict:
    """The word ladder (children): word levels 1–7, then phrase stages 1–3.

    Same 2-up / 2-down staircase as reading, replayed only from word rounds
    (records with exercise_type "words" and a word_level), so it never touches
    the reading level. The Sri Lankan bonus set has no word_level and does not
    move the ladder."""
    t = thresholds()
    level = 1
    strong = weak = 0
    mastered = False
    rounds = 0
    streak_scores: list[int] = []
    history: list[dict] = []

    def move(record: dict, new_level: int | None, direction: str, kind: str, count: int) -> None:
        history.append(
            {
                "at": record["completed_at"],
                "from": word_stage_label(level),
                "to": word_stage_label(new_level) if new_level else "Word ladder completed",
                "direction": direction,
                "reason": _streak_reason(count, kind, "round", streak_scores),
            }
        )

    for record in records:
        if record.get("exercise_type") != "words" or not record.get("word_level"):
            continue
        rounds += 1
        if record["word_level"] != level:
            continue
        if _is_strong(record, t):
            streak_scores = (streak_scores if strong else []) + [record["score"]]
            strong, weak = strong + 1, 0
        elif _is_weak(record, t):
            streak_scores = (streak_scores if weak else []) + [record["score"]]
            strong, weak = 0, weak + 1
        else:
            strong, weak = 0, 0

        if strong >= STRONG_TO_MOVE_UP:
            if level < WORD_LADDER_SIZE:
                move(record, level + 1, "up", "good", STRONG_TO_MOVE_UP)
                level, strong = level + 1, 0
            else:
                if not mastered:
                    move(record, None, "mastered", "good", STRONG_TO_MOVE_UP)
                mastered, strong = True, STRONG_TO_MOVE_UP
        elif weak >= HARD_TO_MOVE_DOWN and level > 1:
            move(record, level - 1, "down", "hard", HARD_TO_MOVE_DOWN)
            level, weak = level - 1, 0

    in_phrases = level > WORD_LEVEL_COUNT
    position = f"Phrase stage {level - WORD_LEVEL_COUNT} of 3" if in_phrases else f"Word level {level} of {WORD_LEVEL_COUNT}"
    if mastered:
        progress_text = "Every word level and phrase stage completed — brilliant!"
    else:
        remaining = STRONG_TO_MOVE_UP - strong
        if level == WORD_LEVEL_COUNT:
            target = "the phrase stage"
        elif level == WORD_LADDER_SIZE:
            target = "finish the word ladder"
        elif in_phrases:
            target = f"phrase stage {level - WORD_LEVEL_COUNT + 1}"
        else:
            target = f"level {level + 1}"
        verb = "" if level == WORD_LADDER_SIZE else "unlock "
        progress_text = (
            f"{position} — {remaining} more good round{'s' if remaining != 1 else ''} to {verb}{target}."
        )
    return {
        "level": level,
        "label": word_stage_label(level),
        "exercise_id": WORD_LADDER_IDS[level],
        "in_phrase_stage": in_phrases,
        "word_levels": WORD_LEVEL_COUNT,
        "ladder_size": WORD_LADDER_SIZE,
        "strong_in_a_row": strong,
        "needed_to_advance": STRONG_TO_MOVE_UP,
        "mastered": mastered,
        "rounds": rounds,
        "progress_text": progress_text,
        "history": history,
    }


def word_level_change_message(before: dict, after: dict) -> str | None:
    if after["level"] > before["level"]:
        return f"Level up! You unlocked {after['label']}. 🌟"
    if after["level"] < before["level"]:
        return f"Let's practise {after['label']} again for a bit — you can climb back up."
    if after["mastered"] and not before["mastered"]:
        return "Amazing — you finished the whole word ladder! 🏆"
    return None


def level_change_message(before: dict, after: dict) -> str | None:
    if after["level_index"] > before["level_index"]:
        return f"Level up! You've unlocked {after['label']} reading."
    if after["level_index"] < before["level_index"]:
        return (
            f"We've moved you back to {after['label']} reading for now, so practice "
            "feels comfortable again. You can work your way back up."
        )
    if after["mastered"] and not before["mastered"]:
        return "Congratulations — you've completed the final stage!"
    return None


def personal_target_wpm(
    base_wpm: int, exercise_id: str, records: list[dict], age_group: str | None = None
) -> int:
    """Adapts the reading speed to the student: strong attempts speed the
    highlight up 10%, difficult ones slow it down 10%."""
    t = thresholds()
    if age_group in PACE_RANGE:
        # Start from a speed that suits the age group: slower for children.
        lo, hi = PACE_RANGE[age_group]
        base_wpm = min(hi, max(lo, base_wpm))
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
    ("mastered", "Fluent speaker", "Completed the final stage of your ladder"),
    ("explorer", "Explorer", "Tried every type of exercise"),
    ("first_words", "First words", "Finished your first word round"),
    ("word_master", "Word master", "Finished all 7 word levels"),
]


# Friendlier titles for children (ages 6–13); descriptions stay the same.
KID_BADGE_TITLES = {
    "first_step": "Super Speaker ⭐",
    "ten_sessions": "Practice Hero 🦸",
    "streak_3": "Three in a Row 🔥",
    "streak_7": "Super Week 🌈",
    "score_90": "Shining Star 🌟",
    "intermediate": "Level Up! 🚀",
    "advanced": "Top Level 🏔️",
    "mastered": "Speaking Champion 🏆",
    "explorer": "Explorer 🧭",
    "first_words": "First Words 🐣",
    "word_master": "Word Wizard 🪄",
}


def earned_badges(
    records: list[dict], level: dict, streak_days: int, best_streak: int, age_group: str | None = None
) -> list[dict]:
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
        # Every kind of exercise available to this age group.
        "explorer": {ex.type.value for ex in exercises_for(age_group or DEFAULT_AGE_GROUP)} <= types,
        "first_words": "words" in types,
        "word_master": word_level_state(records)["level"] > WORD_LEVEL_COUNT,
    }
    kid = age_group == "child"
    return [
        {"id": i, "title": KID_BADGE_TITLES.get(i, t) if kid else t, "description": d, "earned": earned[i]}
        for i, t, d in BADGES
    ]
