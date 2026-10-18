"""Age-bracket therapy: age -> bracket, the 24 exercises, the bracket ladder, fair scoring, tone by age."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component4 import age_bracket_for, answer, attempt_result, build_attempt, build_briefing, build_plan  # noqa: E402
from component4.adaptive import bracket_state, learner_bracket  # noqa: E402
from component4.bracket_tasks import (  # noqa: E402
    BRACKET1_WORDS_PER_SENTENCE, BRACKET2_SENTENCES, BRACKET_EXERCISES, CONSONANT_BLENDS, READING_WORD_RANGES, word_count,
)
from component4.brackets import BRACKETS, TOO_YOUNG_MESSAGE, max_bracket_for, start_bracket  # noqa: E402
from component4.exercises import exercises_for_bracket, get_exercise  # noqa: E402
from component4.scoring import score_with_breakdown  # noqa: E402
from tests.test_component4 import profile  # noqa: E402

STIMULI = Path(__file__).resolve().parents[3] / "speakfree-component1" / "frontend" / "public"
STRONG = {"duration_seconds": 60, "speaking_ratio": 0.85, "self_rating": "easy"}
HARD = {"duration_seconds": 20, "speaking_ratio": 0.2, "self_rating": "hard"}


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def attempts(p, learner, exercise_id, n, payload):
    """Attempt records with increasing timestamps (all after the profile was created)."""
    records, result = [], None
    for i in range(n):
        rec = {**build_attempt(p, {"exercise_id": exercise_id, **payload}), "completed_at": f"2026-10-02T10:{i:02d}:00+00:00"}
        result = attempt_result(p, records, rec, learner)
        records.append(rec)
    return records, result


# --------------------------------------------------------------------------- age -> bracket
@pytest.mark.parametrize("age,bracket", [(6, 1), (7, 1), (8, 2), (9, 2), (10, 3), (11, 3), (12, 4), (13, 4), (14, 5),
                                         (15, 5), (16, 6), (17, 6), (18, 7), (19, 7), (20, 7), (21, 8), (35, 8), (100, 8)])
def test_age_bracket_for_boundaries(age, bracket):
    assert age_bracket_for(age) == bracket


@pytest.mark.parametrize("age", [5, 0, 101])
def test_age_bracket_for_rejects_out_of_range(age):
    with pytest.raises(ValueError) as err:
        age_bracket_for(age)
    if age < 6:
        assert str(err.value) == TOO_YOUNG_MESSAGE == "This app is for ages 6 and above"


# --------------------------------------------------------------------------- the 24 exercises
def test_24_exercises_three_types_per_bracket():
    assert len(BRACKET_EXERCISES) == 24 and len({e["id"] for e in BRACKET_EXERCISES}) == 24
    for b in BRACKETS:
        tasks = exercises_for_bracket(b)
        assert {e["task_type"] for e in tasks} == {"reading", "picture", "conversation"}
        assert all(e["bracket"] == b for e in tasks)
        assert all(get_exercise(e["id"]) is e for e in tasks)


def test_reading_word_counts_are_exact():
    readings = {e["bracket"]: e["passage"] for e in BRACKET_EXERCISES if e["task_type"] == "reading"}
    lo, hi = BRACKET1_WORDS_PER_SENTENCE
    assert all(lo <= word_count(s) <= hi for s in sentences(readings[1])), "bracket 1: 3-4 word sentences"
    lo, hi = BRACKET2_SENTENCES
    assert lo <= len(sentences(readings[2])) <= hi, "bracket 2: 2-3 compound sentences"
    words = re.findall(r"[a-z]+", readings[2].lower())
    assert len({blend for blend in CONSONANT_BLENDS for w in words if w.startswith(blend)}) >= 6, "bracket 2: blends"
    for b, (lo, hi) in READING_WORD_RANGES.items():
        assert lo <= word_count(readings[b]) <= hi, (b, word_count(readings[b]))


def test_target_wpm_rises_with_bracket():
    wpm = [e["target_wpm"] for e in sorted(BRACKET_EXERCISES, key=lambda e: e["bracket"]) if e["task_type"] == "reading"]
    assert wpm == sorted(wpm) and wpm[0] == 70 and wpm[-1] == 150


def test_bracket7_marks_tonal_modulation():
    reading = get_exercise("b7-reading")
    tones = {h["tone"] for h in reading["tone_hints"]}
    assert {"questioning", "excited"} <= tones
    assert all(h["phrase"] in reading["passage"] for h in reading["tone_hints"])


def test_picture_and_conversation_tasks_have_prompts_and_images():
    for e in BRACKET_EXERCISES:
        if e["task_type"] == "reading":
            continue
        assert 3 <= len(e["prompts"]) <= 4, e["id"]
        if e["task_type"] == "picture":
            assert (STIMULI / e["image_url"].lstrip("/")).is_file(), e["image_url"]
        else:
            assert e["situation"]


# --------------------------------------------------------------------------- bracket ladder
def test_start_bracket_from_age_and_severity():
    assert start_bracket(3, 4) == 2  # severe -> one lower
    assert start_bracket(1, 4) == 1  # never below 1
    for severity in (1, 2, 3, None):  # normal / mild / moderate / unknown -> age bracket
        assert start_bracket(3, severity) == 3
    severe = learner_bracket(profile(level=4), [], {"age_bracket": 5})
    assert severe["bracket"] == 4 and severe["start_bracket"] == 4


def test_two_strong_attempts_move_up_one_bracket_capped_at_age_plus_one():
    p = profile(level=2)
    learner = {"age_bracket": 3}
    records, result = attempts(p, learner, "b3-reading", 2, STRONG)
    assert result["level"]["bracket"] == 4 and result["level_message"].startswith("Level up")
    more, result = attempts(p, learner, "b4-picture", 2, STRONG)
    state = learner_bracket(p, records + more, learner)
    assert state["bracket"] == 4 == max_bracket_for(3)  # max = age bracket + 1
    assert state["mastered"] and state["next_bracket"] is None


def test_two_difficult_attempts_move_down_with_minimum_one():
    p = profile(level=2)
    learner = {"age_bracket": 2}
    records, result = attempts(p, learner, "b2-conversation", 2, HARD)
    assert result["level"]["bracket"] == 1
    more, _ = attempts(p, learner, "b1-reading", 2, HARD)
    assert learner_bracket(p, records + more, learner)["bracket"] == 1  # min 1


def test_only_attempts_on_the_current_bracket_count():
    p = profile(level=2)
    learner = {"age_bracket": 3}
    records, _ = attempts(p, learner, "b6-reading", 2, STRONG)  # not the learner's current bracket
    assert learner_bracket(p, records, learner)["bracket"] == 3


def test_therapist_override_wins():
    p = profile(level=2)
    learner = {"age_bracket": 3, "bracket_override": 1}
    records, _ = attempts(p, learner, "b1-reading", 2, STRONG)
    state = learner_bracket(p, records, learner)
    assert state["bracket"] == 1 and state["override"] and state["history"][-1]["direction"] == "therapist"


def test_dashboard_text_is_plain_language():
    state = bracket_state([], age_bracket=3, start=3)
    assert state["dashboard_text"] == (
        "You're practising at Level 3 (ages 10–11 tasks). 2 more strong attempts (score 75+) to unlock Level 4.")


# --------------------------------------------------------------------------- plan
def test_plan_uses_current_bracket_tasks_plus_extras_by_age():
    child = build_plan(profile(disorder="stuttering", level=2), [], learner={"age": 7, "age_bracket": 1})
    adult = build_plan(profile(disorder="stuttering", level=2), [], learner={"age": 35, "age_bracket": 8})
    for plan, b in ((child, 1), (adult, 8)):
        core = [e for e in plan["today"] if e["source"] == "bracket"]
        assert {e["id"] for e in core} == {f"b{b}-reading", f"b{b}-picture", f"b{b}-conversation"}
        assert all(day["exercises"][:3] for day in plan["week"] if day["active"])
    assert "daf" not in {a["id"] for a in child["engine"]["arms"]}  # DAF is not offered to 6-7 year olds
    assert child["learner"]["theme"] == "playful" and adult["learner"]["theme"] == "professional"


def test_therapist_assigned_exercises_come_first():
    plan = build_plan(profile(level=2), [], learner={"age_bracket": 4, "assigned": ["sustained-vowel"]})
    assert plan["today"][0]["id"] == "sustained-vowel" and plan["today"][0]["source"] == "therapist"


def test_bandit_shares_learning_across_brackets():
    p = profile(level=2)
    learner = {"age_bracket": 3}
    records, _ = attempts(p, learner, "b3-picture", 2, STRONG)  # moves up to bracket 4
    arms = {a["id"]: a for a in build_plan(p, records, learner=learner)["engine"]["arms"]}
    assert arms["b4-picture"]["times_practised"] == 2  # arm "core-picture" carries over


# --------------------------------------------------------------------------- fair scoring
def test_free_speech_has_no_rate_penalty():
    base = {"duration_seconds": 60, "speaking_ratio": 0.7, "measured_wpm": 40, "target_wpm": 150}
    reading, _ = score_with_breakdown({**base, "exercise_type": "reading"})
    for kind in ("picture", "conversation"):
        free, parts = score_with_breakdown({**base, "exercise_type": kind})
        assert free > reading and "rate_deviation" not in {x["feature"] for x in parts}


def test_conversation_attempt_is_recorded_with_bracket():
    rec = build_attempt(profile(), {"exercise_id": "b5-conversation", "duration_seconds": 45, "speaking_ratio": 0.6,
                                    "syllables": 80})
    assert rec["bracket"] == 5 and rec["task_type"] == "conversation" and rec["measured_wpm"] is None


# --------------------------------------------------------------------------- tone by age
def test_assistant_tone_follows_age_bracket():
    p = profile(disorder="stuttering")
    young = build_plan(p, [], learner={"age_bracket": 1})
    adult = build_plan(p, [], learner={"age_bracket": 8})
    kid = answer("how am I doing?", "Kavi Silva", p, young, [])
    grown = answer("how am I doing?", "Suresh Perera", p, adult, [])
    assert kid["reply"].startswith("🌟") and kid["tone"] == "playful"
    assert "🌟" not in grown["reply"] and grown["tone"] == "respectful"
    assert build_briefing("Kavi", p, young)["greeting"] == "Hi Kavi! 👋"
    assert build_briefing("Suresh", p, adult)["greeting"] == "Hello Suresh."
    level = answer("what level am I on", "Kavi", p, young, [])
    assert "Level 1" in level["reply"]


def test_llm_prompt_carries_the_age_group():
    from component4 import llm
    from component4.categories import FOCI

    prompt = llm.system_prompt(FOCI["fluency"], {"age_group": "Ages 6–7"}, "playful")
    assert "Ages 6–7" in prompt and "emoji" in prompt and "40 words" in prompt


# --------------------------------------------------------------------------- advanced picture description
def test_one_advanced_picture_per_bracket_with_original_svg():
    from component4.bracket_tasks import ADVANCED_PICTURE_EXERCISES

    assert sorted(e["min_bracket"] for e in ADVANCED_PICTURE_EXERCISES) == list(range(1, 9))
    assert len(BRACKET_EXERCISES) == 24  # the core 8 x 3 is unchanged
    for e in ADVANCED_PICTURE_EXERCISES:
        assert e["type"] == "picture" and e["level"] == "advanced" and e["max_bracket"] == e["min_bracket"]
        assert 3 <= len(e["prompts"]) <= 4 and e["unlock_after"] == f"b{e['min_bracket']}-picture"
        assert (STIMULI / e["image_url"].lstrip("/")).is_file()
    assert get_exercise("b8-picture-advanced")["image_url"].endswith("b8-hospital-adv.svg")


def test_advanced_picture_unlocks_after_the_bracket_picture():
    p, learner = profile(level=2), {"age": 10, "age_bracket": 3}
    lib = {e["id"]: e for e in build_plan(p, [], learner=learner)["library"]}
    assert lib["b3-picture-advanced"]["locked"] and "b4-picture-advanced" not in lib
    records, _ = attempts(p, learner, "b3-picture", 1, {"duration_seconds": 60, "speaking_ratio": 0.6, "self_rating": "ok"})
    plan = build_plan(p, records, learner=learner)
    assert not {e["id"]: e for e in plan["library"]}["b3-picture-advanced"]["locked"]
    assert "b3-picture-advanced" in {a["id"] for a in plan["engine"]["arms"]}
