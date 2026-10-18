"""
Adaptive ladders, replayed from the patient's own attempts.

★ COMPONENT 4 NOVELTY (adaptive learning) - two ladders share one 2-up / 2-down rule:

1. AGE-BRACKET LADDER (bracket_state) - the main practice level, "Level 1-8":
  * start = the learner's age bracket; a Severe screening starts one bracket lower (min 1)
  * 2 strong attempts in a row on the current bracket's tasks -> up one (max: age bracket + 1)
  * 2 difficult attempts in a row                               -> down one (min 1)
  * 2 strong attempts at the top of the range                   -> "mastered" -> re-screen
  * a therapist override pins the bracket (it always wins)

2. SKILL LADDER (level_state) - Beginner -> Intermediate -> Advanced inside the motor-speech
   (clear_speech) and speech-sounds (sound_drill) families. It is replayed the same way:

  * the starting rung comes from Component 3's severity level
      (Severe / Moderate -> Beginner, Mild -> Intermediate, Normal -> Advanced)
  * 2 strong attempts in a row at the current rung  -> move up
  * 2 difficult attempts in a row                    -> move back down
  * 2 strong attempts on Advanced                    -> family mastered -> re-screen suggested
  * the target speed of every passage adapts +/-10 % per strong / difficult attempt

3. WORD LADDER (word_state) - ages 6-11: picture-card rounds, Word Level 1-7 then Phrase Stage
   1-3 (extra_exercises.py). Same 2-up / 2-down rule, replayed from every word round the child
   has done (it is content progression, so a new screening does not reset it).

Only attempts made after the current therapy profile was created are replayed by ladders 1 and 2 -
a new screening restarts them at their starting rungs. Nothing extra is stored.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .brackets import BRACKETS, MAX_BRACKET, MIN_BRACKET, ages_text, clamp_bracket, max_bracket_for, start_bracket
from .exercises import LEVELS
from .extra_exercises import WORD_LADDER_IDS, WORD_LADDER_SIZE, WORD_LEVEL_COUNT, word_stage_label
from .scoring import FREE_SPEECH_TYPES, THRESHOLDS

DEFAULT_AGE_BRACKET = MAX_BRACKET  # age unknown (old callers): no age cap, adult content

LEVEL_LABELS = {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
STREAK_TO_MOVE = 2
PACE_STEP = 0.10
PACE_MIN, PACE_MAX = 0.7, 1.3


def is_strong(record: dict) -> bool:
    return record["score"] >= THRESHOLDS["strong"] and record["self_rating"] != "hard"


def is_weak(record: dict) -> bool:
    return record["score"] < THRESHOLDS["weak"] or record["self_rating"] == "hard"


def _parse(ts: str) -> datetime:
    """Timezone-aware datetime (a stored timestamp without an offset is UTC) - same rule as progress.parse."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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


def word_state(records: list[dict]) -> dict:
    """The children's word ladder: Word Level 1-7, then Phrase Stage 1-3 (bonus rounds never move it)."""
    level = 1
    strong = weak = rounds = 0
    mastered = False
    scores: list[int] = []
    history: list[dict] = []

    for r in records:
        if r.get("exercise_type") != "words" or not r.get("word_level"):
            continue
        rounds += 1
        if r["word_level"] != level:
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
            if level < WORD_LADDER_SIZE:
                history.append({"at": r["completed_at"], "from": word_stage_label(level), "to": word_stage_label(level + 1),
                                "direction": "up",
                                "reason": f"{STREAK_TO_MOVE} good rounds in a row (scores {', '.join(map(str, scores))})"})
                level, strong = level + 1, 0
            else:
                if not mastered:
                    history.append({"at": r["completed_at"], "from": word_stage_label(level), "to": "Word ladder completed",
                                    "direction": "mastered", "reason": "Every word level and phrase stage completed"})
                mastered, strong = True, STREAK_TO_MOVE
        elif weak >= STREAK_TO_MOVE and level > 1:
            history.append({"at": r["completed_at"], "from": word_stage_label(level), "to": word_stage_label(level - 1),
                            "direction": "down",
                            "reason": f"{STREAK_TO_MOVE} hard rounds in a row (scores {', '.join(map(str, scores))})"})
            level, weak = level - 1, 0

    in_phrases = level > WORD_LEVEL_COUNT
    position = (f"Phrase stage {level - WORD_LEVEL_COUNT} of {WORD_LADDER_SIZE - WORD_LEVEL_COUNT}" if in_phrases
                else f"Word level {level} of {WORD_LEVEL_COUNT}")
    if mastered:
        progress_text = "Every word level and phrase stage completed - brilliant!"
    else:
        remaining = STREAK_TO_MOVE - strong
        if level == WORD_LEVEL_COUNT:
            target = "unlock the phrase stage"
        elif level == WORD_LADDER_SIZE:
            target = "finish the word ladder"
        elif in_phrases:
            target = f"unlock phrase stage {level - WORD_LEVEL_COUNT + 1}"
        else:
            target = f"unlock level {level + 1}"
        progress_text = f"{position} - {remaining} more good round{'s' if remaining != 1 else ''} to {target}."
    return {
        "level": level,
        "level_index": level - 1,
        "label": word_stage_label(level),
        "exercise_id": WORD_LADDER_IDS[level],
        "in_phrase_stage": in_phrases,
        "word_levels": WORD_LEVEL_COUNT,
        "ladder_size": WORD_LADDER_SIZE,
        "strong_in_a_row": strong,
        "needed_to_advance": STREAK_TO_MOVE,
        "mastered": mastered,
        "rounds": rounds,
        "progress_text": progress_text,
        "history": history,
    }


def _bracket_label(b: int) -> str:
    return f"Level {b}"


def bracket_state(records: list[dict], age_bracket: int, start: int, since: str | None = None,
                  override: int | None = None) -> dict:
    """The age-bracket ladder (Level 1-8) replayed from the bracket-task attempts."""
    lo, hi = MIN_BRACKET, max_bracket_for(age_bracket)
    bracket = min(max(start, lo), hi)
    since_dt = _parse(since) if since else None
    strong = weak = 0
    mastered = False
    scores: list[int] = []
    reason = (f"Starting level for {ages_text(age_bracket)}." if bracket == age_bracket else
              "Starting one level below your age group so practice begins comfortably.")
    history: list[dict] = [{"at": since, "from": None, "to": _bracket_label(bracket), "direction": "start", "reason": reason}]
    if override:
        override = clamp_bracket(override)

    for r in records:
        if r.get("bracket") is None:
            continue
        if since_dt and _parse(r["completed_at"]) < since_dt:
            continue
        if r["bracket"] != (override or bracket):
            continue
        if is_strong(r):
            scores = (scores if strong else []) + [r["score"]]
            strong, weak = strong + 1, 0
        elif is_weak(r):
            scores = (scores if weak else []) + [r["score"]]
            strong, weak = 0, weak + 1
        else:
            strong = weak = 0
        if override:  # therapist override: the level is pinned, streaks are only reported
            continue
        if strong >= STREAK_TO_MOVE:
            if bracket < hi:
                history.append({"at": r["completed_at"], "from": _bracket_label(bracket), "to": _bracket_label(bracket + 1),
                                "direction": "up",
                                "reason": f"{STREAK_TO_MOVE} strong attempts in a row (scores {', '.join(map(str, scores))})"})
                bracket, strong = bracket + 1, 0
            else:
                if not mastered:
                    history.append({"at": r["completed_at"], "from": _bracket_label(bracket), "to": "Mastered",
                                    "direction": "mastered", "reason": "Top level for your age completed"})
                mastered, strong = True, STREAK_TO_MOVE
        elif weak >= STREAK_TO_MOVE and bracket > lo:
            history.append({"at": r["completed_at"], "from": _bracket_label(bracket), "to": _bracket_label(bracket - 1),
                            "direction": "down",
                            "reason": f"{STREAK_TO_MOVE} difficult attempts in a row (scores {', '.join(map(str, scores))})"})
            bracket, weak = bracket - 1, 0

    if override:
        history.append({"at": None, "from": None, "to": _bracket_label(override),
                        "direction": "therapist", "reason": "Level chosen by your therapist"})
        bracket, mastered = override, False
        strong = min(strong, STREAK_TO_MOVE)

    nxt = bracket + 1 if bracket < hi and not override else None
    remaining = max(0, STREAK_TO_MOVE - strong)
    now_text = f"You're practising at Level {bracket} ({ages_text(bracket)} tasks)."
    if override:
        progress_text = "Your therapist chose this level for you."
    elif mastered:
        progress_text = "You've completed the top level for your age - great work! A new screening will show your progress."
    elif nxt:
        progress_text = (f"{remaining} more strong attempt{'s' if remaining != 1 else ''} "
                         f"(score {THRESHOLDS['strong']}+) to unlock Level {nxt}.")
    else:
        progress_text = (f"This is the top level for your age. {remaining} more strong attempt{'s' if remaining != 1 else ''} "
                         f"(score {THRESHOLDS['strong']}+) to complete it.")
    return {
        "bracket": bracket,
        "level_index": bracket - 1,
        "label": _bracket_label(bracket),
        "ages": ages_text(bracket),
        "bracket_label": BRACKETS[bracket]["label"],
        "age_bracket": age_bracket,
        "start_bracket": min(max(start, lo), hi),
        "min_bracket": lo,
        "max_bracket": hi,
        "next_bracket": nxt,
        "override": bool(override),
        "strong_in_a_row": strong,
        "weak_in_a_row": weak,
        "needed_to_advance": STREAK_TO_MOVE,
        "mastered": mastered,
        "progress_text": progress_text,
        "dashboard_text": f"{now_text} {progress_text}",
        "target_wpm": BRACKETS[bracket]["target_wpm"],
        "strong_threshold": THRESHOLDS["strong"],
        "weak_threshold": THRESHOLDS["weak"],
        "history": history,
    }


def learner_bracket(profile: dict, records: list[dict], learner: dict | None = None) -> dict:
    """Bracket ladder for one learner: age bracket + screening severity -> start, then replay."""
    learner = learner or {}
    age_bracket = int(learner.get("age_bracket") or DEFAULT_AGE_BRACKET)
    start = start_bracket(age_bracket, profile.get("severity_level"))
    return bracket_state(records, age_bracket, start, profile.get("created_at"), learner.get("bracket_override"))


def level_change_message(before: dict, after: dict) -> str | None:
    if after["level_index"] > before["level_index"]:
        if after.get("bracket"):
            return f"Level up! You've unlocked {after['label']} ({after['ages']} tasks)."
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
        if wpm and target and attempt.get("exercise_type") not in FREE_SPEECH_TYPES:
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
    if attempt.get("exercise_type") == "words" and attempt.get("items_total"):
        got = attempt.get("items_clear") or 0
        notes.append(f"You said {got} of {attempt['items_total']} words well." +
                     (" Super!" if got >= 0.75 * attempt["items_total"] else " Every round makes them easier."))
    if duration < 15:
        notes.append("That was quite short - try practising for a bit longer next time.")
    if attempt.get("self_rating") == "easy":
        notes.append("You said this felt easy - a great sign you're ready for more challenge.")
    elif attempt.get("self_rating") == "hard":
        notes.append("You said this felt hard. We'll keep practising at a comfortable level.")
    return notes
