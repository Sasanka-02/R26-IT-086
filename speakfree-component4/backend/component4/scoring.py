"""
Practice-quality score for one therapy attempt (0-100), fully explainable.

    score = clip( w · x , 0, 100 )

    x = [ 1,                 intercept
          live,              1 if live audio metrics exist
          voicing,           fraction of time the voice was active (0-1)
          pauses_per_min,    long pauses (>= 3 s silence) per minute
          quiet_per_min,     "too quiet" warnings per minute
          rate_deviation,    |measured wpm - target wpm| / target wpm (0-1)
          rating,            self-rating: easy +1, okay 0, hard -1
          short_attempt,     1 if the attempt lasted < 15 s
          goal_gap ]         goal completion - 0.75  (sustained vowel: seconds held / target;
                             sound drills: words marked clear / words practised)

The prior weights come from the original Component 4 viva guide (calibrated against therapist
ratings there). `goal_gap` is new for the integrated platform: reaching 75 % of an exercise's
goal is neutral, every 10 % above / below adds / removes 4 points.

Fairness for spontaneous speech: picture and conversation tasks have no fixed text, so there is
no "right" speed to compare against - their rate_deviation is always 0 (never a penalty).
"""
from __future__ import annotations

FEATURES = ["intercept", "live", "voicing", "pauses_per_min", "quiet_per_min",
            "rate_deviation", "rating", "short_attempt", "goal_gap"]

FEATURE_LABELS = {
    "intercept": "Base score",
    "live": "Live-audio exercise",
    "voicing": "Voice active (fraction of time)",
    "pauses_per_min": "Long pauses per minute",
    "quiet_per_min": "Too-quiet warnings per minute",
    "rate_deviation": "Speech-rate deviation from target",
    "rating": "Self-rating (easy +1 / hard -1)",
    "short_attempt": "Attempt shorter than 15 s",
    "goal_gap": "Exercise goal reached (vs 75 %)",
}

WEIGHTS = {
    "intercept": 72.0,
    "live": -32.0,
    "voicing": 85.0,
    "pauses_per_min": -10.0,
    "quiet_per_min": -4.0,
    "rate_deviation": -30.0,
    "rating": 12.0,
    "short_attempt": -15.0,
    "goal_gap": 40.0,
}
THRESHOLDS = {"strong": 75, "weak": 45}
SHORT_ATTEMPT_SECONDS = 15
RATING_VALUE = {"easy": 1.0, "ok": 0.0, "hard": -1.0}
FREE_SPEECH_TYPES = ("picture", "conversation")  # no target text -> no speed target


def goal_completion(attempt: dict) -> float | None:
    if attempt.get("exercise_type") == "sustained_vowel" and attempt.get("max_phonation_sec") is not None:
        target = float(attempt.get("target_seconds") or 10)
        return min(1.0, float(attempt["max_phonation_sec"]) / target)
    if attempt.get("exercise_type") == "sound_drill" and attempt.get("items_total"):
        return min(1.0, float(attempt.get("items_clear") or 0) / float(attempt["items_total"]))
    return None


def extract_features(attempt: dict) -> dict[str, float]:
    duration = float(attempt.get("duration_seconds") or 0)
    minutes = max(duration / 60, 0.25)
    ratio = attempt.get("speaking_ratio")
    live = ratio is not None
    wpm, target = attempt.get("measured_wpm"), attempt.get("target_wpm")
    fixed_text = attempt.get("exercise_type") not in FREE_SPEECH_TYPES
    goal = goal_completion(attempt)
    return {
        "intercept": 1.0,
        "live": 1.0 if live else 0.0,
        "voicing": float(ratio) if live else 0.0,
        "pauses_per_min": (attempt.get("long_pauses", 0) / minutes) if live else 0.0,
        "quiet_per_min": (attempt.get("quiet_warnings", 0) / minutes) if live else 0.0,
        "rate_deviation": min(1.0, abs(wpm - target) / target) if live and fixed_text and wpm and target else 0.0,
        "rating": RATING_VALUE.get(attempt.get("self_rating", "ok"), 0.0),
        "short_attempt": 1.0 if duration < SHORT_ATTEMPT_SECONDS else 0.0,
        "goal_gap": (goal - 0.75) if goal is not None else 0.0,
    }


def score_with_breakdown(attempt: dict) -> tuple[int, list[dict]]:
    """Score plus each feature's contribution, so the result is explainable."""
    feats = extract_features(attempt)
    parts = [
        {"feature": f, "label": FEATURE_LABELS[f], "value": round(feats[f], 3),
         "weight": WEIGHTS[f], "points": round(feats[f] * WEIGHTS[f], 1)}
        for f in FEATURES if feats[f] != 0
    ]
    raw = sum(p["points"] for p in parts)
    return int(round(max(0.0, min(100.0, raw)))), parts


def verdict(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= THRESHOLDS["strong"] - 10:
        return "Good"
    if score >= THRESHOLDS["weak"]:
        return "Getting there"
    return "A tough one - that's okay"
