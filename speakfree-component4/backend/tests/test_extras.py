"""Unit tests for the features carried over from the stand-alone prototype."""
from datetime import datetime, timedelta, timezone

import numpy as np

from component4.adaptive import word_state
from component4.dashboard import badges, best_streak, first_vs_latest, report_card, weekly
from component4.evaluation import agreement, inter_rater, sus_band, sus_score, weighted_kappa
from component4.exercises import exercises_for, get_exercise, suits_bracket
from component4.privacy import calibrate_daf, fingerprint, release, true_stats
from component4.scoring import score_with_breakdown
from component4.therapist import alerts, goal_progress, homework_status

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def rec(exercise_id="words-1", score=80, rating="ok", days_ago=0, **extra):
    return {"exercise_id": exercise_id, "exercise_type": extra.pop("exercise_type", "words"), "title": exercise_id,
            "score": score, "self_rating": rating, "duration_seconds": 60,
            "completed_at": (NOW - timedelta(days=days_ago)).isoformat(), **extra}


def test_extra_exercises_respect_age_ranges():
    words, roleplay = get_exercise("words-1"), get_exercise("adult-meeting")
    assert suits_bracket(words, 3) and not suits_bracket(words, 4)
    assert suits_bracket(roleplay, 7) and not suits_bracket(roleplay, 6)
    assert suits_bracket(get_exercise("teen-roleplay-interview"), 6) and not suits_bracket(get_exercise("teen-roleplay-interview"), 5)
    ids = [e["id"] for e in exercises_for(None)]
    assert len(ids) == len(set(ids))


def test_word_ladder_two_up_two_down():
    assert word_state([])["level"] == 1
    up = [rec(word_level=1, score=85), rec(word_level=1, score=82)]
    state = word_state(up)
    assert state["level"] == 2 and state["history"][0]["direction"] == "up" and state["exercise_id"] == "words-2"
    down = up + [rec(word_level=2, score=30, rating="hard"), rec(word_level=2, score=35, rating="hard")]
    assert word_state(down)["level"] == 1
    bonus = up + [rec("words-sri-lanka", word_level=None)]
    assert word_state(bonus)["rounds"] == 2  # bonus rounds never move the ladder


def test_word_rounds_score_from_items_without_live_audio():
    good, _ = score_with_breakdown({"exercise_type": "words", "duration_seconds": 40, "self_rating": "ok",
                                    "items_total": 10, "items_clear": 10})
    poor, _ = score_with_breakdown({"exercise_type": "words", "duration_seconds": 40, "self_rating": "ok",
                                    "items_total": 10, "items_clear": 2})
    assert good >= 75 > poor


def test_dashboard_report_card_and_badges():
    level = {"label": "Level 3", "progress_text": "x", "history": [], "mastered": False}
    assert report_card([], level, None, NOW)["label"] == "Getting started"
    idle = report_card([rec(days_ago=10)] * 4, level, None, NOW)
    assert idle["status"] == "needs_support" and "10 days" in idle["headline"]
    rising = [rec(score=s, days_ago=6 - i) for i, s in enumerate([50, 52, 51, 70, 75, 80])]
    assert report_card(rising, level, {"title": "Next", "reason": "Because."}, NOW)["status"] == "improving"
    earned = {b["id"]: b["earned"] for b in badges(rising, level, None, None, {"words"}, playful=False)}
    assert earned["first_step"] and earned["explorer"] and "first_words" not in earned
    kid = badges(rising, level, None, word_state(rising), {"words"}, playful=True)
    assert any("⭐" in b["title"] for b in kid)
    assert best_streak(rising) == 6 and weekly(rising, NOW)[0]["sessions"] == 6
    assert first_vs_latest(rising)[0]["change"] == 30


def test_homework_goals_and_alerts():
    items = [{"exercise_id": "daf", "assigned_at": (NOW - timedelta(days=3)).isoformat(), "due": "2026-10-17", "times": 2}]
    records = [rec("daf", exercise_type="daf", days_ago=5), rec("daf", exercise_type="daf", days_ago=1)]
    hw = homework_status(items, records, NOW.date(), {"daf": {"title": "DAF", "type": "daf"}})[0]
    assert hw["done_count"] == 1 and hw["overdue"] and hw["title"] == "DAF"
    goals = goal_progress([{"id": 1, "metric": "average_score", "target": 70}], records, NOW)
    assert goals[0]["met"] and goals[0]["source"] == "therapist"
    dropping = [rec(score=s, days_ago=9) for s in (90, 80, 70, 60)]
    kinds = {a["kind"] for a in alerts("Kasun Perera", dropping, [hw], NOW)}
    assert {"inactive", "score_drop", "homework_overdue"} <= kinds


def test_evaluation_statistics():
    assert sus_score([5, 1] * 5) == 100 and sus_score([3] * 10) == 50 and sus_band(72) == "Good"
    assert weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == 1.0
    assert inter_rater({1: [4, 4], 2: [2, 3], 3: [5]})["pairs"] == 2
    rng = np.random.default_rng(0)
    rated = []
    for _ in range(12):
        ratio = float(rng.uniform(0.3, 0.9))
        record = {"exercise_type": "reading", "speaking_ratio": ratio, "duration_seconds": 60, "long_pauses": 1,
                  "self_rating": "ok", "measured_wpm": 100, "target_wpm": 110}
        score, _ = score_with_breakdown(record)
        rated.append({"record": record, "score": score, "rating": int(np.clip(round(1 + ratio * 5), 1, 5))})
    out = agreement(rated)
    assert out["current"]["mae"] >= 0 and out["calibrated"]["mae"] >= 0 and len(out["weights"]) == 9


def test_daf_calibration_and_private_release():
    trials = [{"delay_ms": 50, "stutter_events": 0, "speech_rate_wpm": 160},
              {"delay_ms": 150, "stutter_events": 0, "speech_rate_wpm": 128}]
    assert calibrate_daf(trials)["recommended_delay_ms"] == 150  # tie on events -> closest to the target rate
    stats = true_stats([rec(score=70), rec(score=90)], [3, 3], {"words": "Word practice"})
    fp = fingerprint([1, 2])
    a, b = release(stats, 1.0, fp, {"words": "Word practice"}), release(stats, 1.0, fp, {"words": "Word practice"})
    assert a["mean_score"] == b["mean_score"] and len(a["accuracy"]) == 5


def test_every_exercise_has_help_with_examples_per_prompt():
    from component4 import build_plan
    from component4.bracket_tasks import ADVANCED_PICTURE_EXERCISES, BRACKET_EXERCISES
    from component4.help import EXAMPLES, help_for
    from tests.test_component4 import profile

    for ex in BRACKET_EXERCISES + ADVANCED_PICTURE_EXERCISES:
        if ex["type"] in ("picture", "conversation"):
            assert len(EXAMPLES[ex["id"]]) == len(ex["prompts"]), ex["id"]
    for bracket in range(1, 9):
        plan = build_plan(profile(level=2), [], learner={"age_bracket": bracket})
        for ex in plan["today"] + plan["library"]:
            h = ex["help"]
            assert len(h["steps"]) >= 3 and h["model"], ex["id"]
            if ex["type"] in ("picture", "conversation", "roleplay", "sound_drill", "words"):
                assert h["examples"], ex["id"]
    assert help_for({"id": "x", "type": "reading", "passage": "Mum has a map."})["model"] == "Mum has a map."
