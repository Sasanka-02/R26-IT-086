"""Component 4 tests: C3 -> profile, adaptive ladder, bandit + category prior, plan, assistant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component4 import answer, attempt_result, build_attempt, build_briefing, build_plan, build_profile  # noqa: E402
from component4.categories import focus_probabilities  # noqa: E402
from component4.exercises import sound_drills  # noqa: E402
from component4.scoring import score_with_breakdown  # noqa: E402

CREATED = "2026-10-01T00:00:00+00:00"


def c3(disorder="stuttering", level=3, probs=None, sounds=()):
    probs = probs or {"normal": 0.1, "stuttering": 0.1, "dysarthria": 0.1, "articulation": 0.1, disorder: 0.7}
    return {"primary_disorder": disorder, "severity_level": level, "severity_label": "x", "confidence_score": 0.7,
            "disorder_breakdown": probs,
            "flagged_sounds": [{"sound": s, "accuracy_percent": 50 + i} for i, s in enumerate(sounds)]}


def profile(**kw):
    return build_profile(c3(**kw), {"fluency_score": 60, "overall_speech_score": 65},
                         {"session_articulation": {"score": 70}}, created_at=CREATED, session_id="s1")


def practise(p, exercise_id, n, **payload):
    records = []
    result = None
    for _ in range(n):
        rec = build_attempt(p, {"exercise_id": exercise_id, **payload})
        result = attempt_result(p, records, rec)
        records.append(rec)
    return records, result


def test_profile_maps_disorder_and_severity():
    p = profile(disorder="dysarthria", level=4)
    assert p["focus"] == "motor_speech"
    assert p["start_level"] == "beginner"
    assert profile(disorder="normal", level=1)["start_level"] == "advanced"
    assert abs(sum(p["focus_probabilities"].values()) - 1) < 1e-6


def test_focus_probabilities_rekeyed():
    fp = focus_probabilities({"normal": 0.2, "stuttering": 0.8}, "fluency")
    assert fp["fluency"] == 0.8 and fp["maintenance"] == 0.2


def test_sound_drills_follow_flagged_sounds():
    drills = sound_drills(["/r/", "/θ/ (th)"])
    assert {d["sound"] for d in drills} == {"/r/", "/θ/ (th)"}
    assert len(drills) == 6


def test_scoring_goal_gap_for_drills():
    good, _ = score_with_breakdown({"exercise_type": "sound_drill", "duration_seconds": 60, "items_total": 8, "items_clear": 8})
    poor, _ = score_with_breakdown({"exercise_type": "sound_drill", "duration_seconds": 60, "items_total": 8, "items_clear": 2})
    assert good > poor


def test_skill_ladder_moves_up_after_two_strong_attempts():
    p = profile(disorder="dysarthria", level=3)  # skill ladder starts at Beginner
    _, result = practise(p, "clear-beginner", 2, duration_seconds=60, speaking_ratio=0.8, syllables=120,
                         self_rating="easy")
    assert result["skill_level"]["level"] == "intermediate"
    assert result["level_message"].startswith("Level up")


def test_skill_ladder_moves_down_after_two_hard_attempts():
    p = profile(disorder="dysarthria", level=2)  # starts intermediate
    _, result = practise(p, "clear-intermediate", 2, duration_seconds=20, speaking_ratio=0.2, self_rating="hard")
    assert result["skill_level"]["level"] == "beginner"


def test_first_plan_follows_c3_category_prior():
    for disorder, family in (("stuttering", {"pacing", "daf", "sustained_vowel"}), ("dysarthria", {"clear_speech"}),
                             ("articulation", {"sound_drill"})):
        plan = build_plan(profile(disorder=disorder, sounds=("/s/",)), [])
        core = [e for e in plan["today"] if e["source"] == "bracket"]
        assert {e["task_type"] for e in core} == {"reading", "picture", "conversation"}
        extras = plan["today"][len(core):]
        assert family & {e["type"] for e in extras}, (disorder, [e["id"] for e in extras])
        assert all(set(e["focus"]) & {plan["focus"]["key"]} for e in plan["today"])


def test_dose_scales_with_severity():
    assert build_plan(profile(level=4), [])["dose"]["sessions_per_week"] > build_plan(profile(level=1), [])["dose"]["sessions_per_week"]


def test_bandit_learns_from_scores():
    p = profile(disorder="stuttering", level=3)
    good, _ = practise(p, "pacing-easy", 3, duration_seconds=60, speaking_ratio=0.85, self_rating="easy")
    bad, _ = practise(p, "daf", 3, duration_seconds=5, self_rating="hard")
    plan = build_plan(p, good + bad)
    arms = {a["id"]: a for a in plan["engine"]["arms"]}
    assert arms["pacing-easy"]["expected_reward"] > arms["daf"]["expected_reward"]
    assert len(plan["engine"]["context"]["vector"]) == 7


def test_rescreen_after_many_attempts():
    p = profile()
    records, _ = practise(p, "picture-park", 12, duration_seconds=40, speaking_ratio=0.6)
    assert build_plan(p, records)["rescreen"]["recommended"] is True


def test_assistant_is_category_aware_and_never_names_disorder():
    p = profile(disorder="articulation", sounds=("/r/",))
    plan = build_plan(p, [])
    reply = answer("how do I say my sound?", "Ann", p, plan, [])
    assert reply["source"] == "classifier" and "'R'" in reply["reply"]
    brief = build_briefing("Ann", p, plan)
    text = " ".join(brief["summary"]).lower()
    for word in ("articulation disorder", "dysarthria", "stuttering", "severity"):
        assert word not in text
    assert answer("why am I doing these exercises", "Ann", p, plan, [])["intent"] == "explain_focus"
