"""Storage-agnostic Component 4 operations used by the platform's therapy routes."""
from __future__ import annotations

from datetime import datetime, timezone

from .adaptive import attempt_feedback, learner_bracket, level_change_message, word_state
from .exercises import get_exercise, syllables_per_word
from .plan import skill_state
from .scoring import score_with_breakdown, verdict


def _measured_wpm(exercise: dict, syllables: int | None, duration: float) -> int | None:
    if not syllables or not exercise.get("passage") or duration < 5:
        return None
    words = syllables / syllables_per_word(exercise["passage"])
    return int(round(words / (duration / 60)))


def build_attempt(profile: dict, payload: dict, live_summary: dict | None = None) -> dict:
    """Turn the browser's numbers (+ the live WebSocket summary) into a scored attempt record."""
    exercise = get_exercise(payload["exercise_id"], profile.get("flagged_sounds"))
    if exercise is None:
        raise KeyError(payload["exercise_id"])
    live = live_summary or {}
    speaking_ratio = payload.get("speaking_ratio")
    if speaking_ratio is None and live.get("speaking_ratio") is not None and live.get("duration_seconds", 0) > 0:
        speaking_ratio = live["speaking_ratio"]
    duration = float(payload.get("duration_seconds") or live.get("duration_seconds") or 0)
    syllables = payload.get("syllables") if payload.get("syllables") is not None else live.get("syllables")
    attempt = {
        "exercise_id": exercise["id"],
        "exercise_type": exercise["type"],
        "focus": profile.get("focus"),
        "title": exercise["title"],
        "level": exercise.get("level"),
        "bracket": exercise.get("bracket"),
        "task_type": exercise.get("task_type"),
        "word_level": exercise.get("word_level"),
        "difficulty": exercise.get("difficulty", 1),
        "duration_seconds": round(duration, 1),
        "speaking_ratio": round(float(speaking_ratio), 3) if speaking_ratio is not None else None,
        "long_pauses": int(payload.get("long_pauses") or live.get("pause_count") or 0),
        "quiet_warnings": int(payload.get("quiet_warnings") or live.get("quiet_warnings") or 0),
        "syllables": syllables,
        "measured_wpm": _measured_wpm(exercise, syllables, duration),
        "target_wpm": payload.get("target_wpm") or exercise.get("target_wpm"),
        "target_seconds": exercise.get("target_seconds"),
        "max_phonation_sec": payload.get("max_phonation_sec") if payload.get("max_phonation_sec") is not None
        else live.get("max_phonation_sec"),
        "items_total": payload.get("items_total"),
        "items_clear": payload.get("items_clear"),
        "self_rating": payload.get("self_rating", "ok"),
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    score, breakdown = score_with_breakdown(attempt)
    return {**attempt, "score": score, "score_breakdown": breakdown}


def attempt_result(profile: dict, records_before: list[dict], stored: dict, learner: dict | None = None) -> dict:
    """Score + feedback + the level change this attempt caused (age-bracket ladder, then skill / word ladder)."""
    records_after = records_before + [stored]
    before = learner_bracket(profile, records_before, learner)
    after = learner_bracket(profile, records_after, learner)
    skill_before, skill_after = skill_state(profile, records_before), skill_state(profile, records_after)
    message = level_change_message(before, after)
    if message is None and skill_before and skill_after:
        message = level_change_message(skill_before, skill_after)
    if message is None and stored.get("exercise_type") == "words":
        message = level_change_message(word_state(records_before), word_state(records_after))
    return {
        "record": stored,
        "score": stored["score"],
        "verdict": verdict(stored["score"]),
        "feedback": attempt_feedback(stored),
        "breakdown": stored["score_breakdown"],
        "level": after,
        "skill_level": skill_after,
        "level_message": message,
    }
