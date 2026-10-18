"""Unit tests for the features carried over from the stand-alone prototype."""
from datetime import datetime, timedelta, timezone

import numpy as np

from component4.adaptive import word_state
from component4.dashboard import badges, best_streak, first_vs_latest, report_card, weekly
from component4.evaluation import agreement, inter_rater, sus_band, sus_score, weighted_kappa
from component4.exercises import exercises_for, require_exercise, suits_bracket
from component4.privacy import calibrate_daf, fingerprint, release, true_stats
from component4.scoring import score_with_breakdown
from component4.therapist import alerts, goal_progress, homework_status

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def rec(exercise_id="words-1", score=80, rating="ok", days_ago=0, **extra):
    return {"exercise_id": exercise_id, "exercise_type": extra.pop("exercise_type", "words"), "title": exercise_id,
            "score": score, "self_rating": rating, "duration_seconds": 60,
            "completed_at": (NOW - timedelta(days=days_ago)).isoformat(), **extra}


def test_extra_exercises_respect_age_ranges():
    words, roleplay = require_exercise("words-1"), require_exercise("adult-meeting")
    assert suits_bracket(words, 3) and not suits_bracket(words, 4)
    assert suits_bracket(roleplay, 7) and not suits_bracket(roleplay, 6)
    interview = require_exercise("teen-roleplay-interview")
    assert suits_bracket(interview, 6) and not suits_bracket(interview, 5)
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


def test_llm_falls_back_offline_on_truncation_refusal_and_errors(monkeypatch):
    """llm.ask returns the model text, or None (offline answer) when cut off, refused or broken."""
    import types

    from component4 import llm
    from component4.categories import FOCI

    class APIError(Exception):
        pass

    def fake_sdk(result):
        class Client:
            def __init__(self, **kw):
                self.kw = kw
                self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self.create))

            def create(self, **kw):
                assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
                if isinstance(result, Exception):
                    raise result
                return result

        return types.SimpleNamespace(Anthropic=Client, RateLimitError=APIError, APIStatusError=APIError,
                                     APIConnectionError=APIError)

    def reply(stop, text="Keep going!"):
        return types.SimpleNamespace(stop_reason=stop, content=[types.SimpleNamespace(type="thinking"),
                                                                types.SimpleNamespace(type="text", text=text)])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    for result, expected in ((reply("end_turn"), "Keep going!"), (reply("max_tokens", "Keep go"), None),
                             (reply("refusal"), None), (TypeError("unexpected keyword 'fallbacks'"), None)):
        monkeypatch.setattr(llm, "anthropic", fake_sdk(result))
        monkeypatch.setattr(llm, "_client", None)
        assert llm.ask("how am I doing?", "Kavi", FOCI["fluency"], {"age_group": "Ages 6–7"}, "playful") == expected
    assert llm._get_client().kw == {"timeout": 30.0, "max_retries": 1}


def test_live_pauses_counted_once_per_silence_and_not_before_speaking():
    from component4.realtime_feedback import process_metric, summarize
    from component4.schemas import LiveMetric
    from component4.session_store import LiveSessionState

    def run(flags):
        state = LiveSessionState(session_id="t")
        for i, speaking in enumerate(flags):
            process_metric(state, LiveMetric(timestamp_ms=i * 500, rms_energy=0.05 if speaking else 0.001,
                                             zero_crossing_rate=0.1, is_speaking=speaking))
        return state

    # 4 s silence while getting ready, speech, a 10 s silence, speech again -> exactly one long pause
    state = run([False] * 8 + [True] * 6 + [False] * 20 + [True] * 4)
    assert state.pause_count == 1
    assert run([True] * 4 + [False] * 6 + [True] + [False] * 6).pause_count == 2
    assert summarize(LiveSessionState(session_id="empty"))["speaking_ratio"] is None


def test_stale_live_sessions_are_dropped():
    from component4 import session_store

    old = session_store.start_session("old")
    old.started_at -= session_store.MAX_AGE_SECONDS + 1
    session_store.start_session("new")
    assert session_store.get_session("old") is None and session_store.end_session("new") is not None


def test_focus_probabilities_fall_back_when_breakdown_is_unusable():
    from component4.categories import focus_probabilities

    for breakdown in ({"unknown": 0.9}, {"stuttering": 0.0, "normal": 0.0}):
        assert focus_probabilities(breakdown, "fluency") == {"fluency": 1.0, "motor_speech": 0.0,
                                                             "speech_sounds": 0.0, "maintenance": 0.0}


def test_naive_timestamps_compare_with_aware_ones():
    from component4.adaptive import level_state

    rec = {"exercise_type": "clear_speech", "level": "beginner", "score": 90, "self_rating": "ok",
           "completed_at": "2026-10-02T10:00:00"}  # stored without an offset
    state = level_state([rec, {**rec, "completed_at": "2026-10-02T11:00:00"}], "clear_speech", since="2026-10-01T00:00:00+00:00")
    assert state["level"] == "intermediate"


def test_badge_question_uses_the_real_badges():
    from component4 import answer, build_plan
    from tests.test_component4 import profile

    p = profile(level=2)
    plan = build_plan(p, [], learner={"age_bracket": 5})
    reply = answer("what badges do i have", "Ravi Kumar", p, plan, [])
    assert reply["source"] == "classifier" and "0 of" in reply["reply"] and "First step" in reply["reply"]
