from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import level_state, personal_target_wpm, word_level_state
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.simulation import evaluate

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def reading(level, score, rating="ok", minutes=0, exercise_id=None):
    return {
        "exercise_id": exercise_id or f"reading-{level}",
        "exercise_type": "reading",
        "level": level,
        "score": score,
        "self_rating": rating,
        "completed_at": (T0 + timedelta(minutes=minutes)).isoformat(),
    }


def test_starts_at_beginner():
    assert level_state([])["level"] == "beginner"


def test_one_strong_reading_levels_up():
    state = level_state([reading("beginner", 90, minutes=1)])
    assert state["level"] == "intermediate"
    assert state["history"][0]["reason"] == "after 1 strong Beginner reading (score 90)"


def test_average_reading_does_not_level_up():
    records = [reading("beginner", 60, minutes=1), reading("beginner", 65, minutes=2)]
    assert level_state(records)["level"] == "beginner"


def test_one_hard_reading_does_not_move_down():
    records = [reading("beginner", 90, minutes=1), reading("intermediate", 30, "hard", minutes=2)]
    assert level_state(records)["level"] == "intermediate"


def test_hard_readings_move_back_down():
    records = [
        reading("beginner", 90, minutes=1), reading("beginner", 90, minutes=2),
        reading("intermediate", 30, "hard", minutes=3), reading("intermediate", 35, "hard", minutes=4),
    ]
    assert level_state(records)["level"] == "beginner"


def test_final_stage_mastered():
    records = [reading(lvl, 95, minutes=i) for i, lvl in enumerate(
        ["beginner", "beginner", "intermediate", "intermediate", "advanced", "advanced"])]
    state = level_state(records)
    assert state["level"] == "advanced" and state["mastered"]


def test_therapist_override_sets_level_and_ignores_older_attempts():
    records = [reading("beginner", 90, minutes=1), reading("beginner", 90, minutes=2)]
    override = {"level": "beginner", "at": (T0 + timedelta(minutes=5)).isoformat()}
    state = level_state(records, override)
    assert state["level"] == "beginner" and state["set_by_therapist"]


def test_personal_pace_adapts():
    strong = [{**reading("beginner", 95, minutes=i)} for i in range(2)]
    weak = [{**reading("beginner", 20, "hard", minutes=i)} for i in range(2)]
    assert personal_target_wpm(100, "reading-beginner", strong) == 120
    assert personal_target_wpm(100, "reading-beginner", weak) == 80


def test_plan_puts_therapist_assignment_first():
    settings = {"assigned": [{"exercise_id": "daf-1"}], "level_override": None}
    plan = recommend_weekly_plan([], settings)
    assert plan["exercises"][0]["id"] == "daf-1"
    assert plan["exercises"][0]["source"] == "therapist"
    assert any(e["id"] == "reading-beginner" for e in plan["exercises"])


def test_plan_items_are_explained():
    plan = recommend_weekly_plan([])
    for item in plan["exercises"]:
        assert item["reason"]
        assert item["uncertainty"] is not None


def test_linucb_beats_random_and_rotation_in_simulation():
    result = {row["strategy"]: row for row in evaluate(n_students=30, rounds=25)["summary"]}
    assert result["linucb"]["average_reward"] > result["random"]["average_reward"]
    assert result["linucb"]["cumulative_regret"] < result["rotation"]["cumulative_regret"]


# --- Word ladder (children) ------------------------------------------------

def word_round(word_level, score, rating="ok", minutes=0):
    return {
        "exercise_id": f"words-{word_level}",
        "exercise_type": "words",
        "level": None,
        "word_level": word_level,
        "score": score,
        "self_rating": rating,
        "completed_at": (T0 + timedelta(minutes=minutes)).isoformat(),
    }


def test_word_ladder_starts_at_level_1():
    state = word_level_state([])
    assert state["level"] == 1 and state["exercise_id"] == "words-1"
    assert state["progress_text"].startswith("Word level 1 of 7")


def test_one_good_word_round_moves_up_and_two_hard_move_down():
    records = [word_round(1, 90, minutes=1)]
    assert word_level_state(records)["level"] == 2
    records += [word_round(2, 30, "hard", minutes=3), word_round(2, 35, "hard", minutes=4)]
    state = word_level_state(records)
    assert state["level"] == 1
    assert [h["direction"] for h in state["history"]] == ["up", "down"]


def test_word_progress_text_counts_remaining_rounds():
    records = [word_round(1, 90, minutes=1), word_round(2, 90, minutes=2), word_round(3, 30, "hard", minutes=3)]
    assert word_level_state(records)["progress_text"] == (
        "Word level 3 of 7 — 1 more good round to unlock level 4."
    )


def test_word_ladder_continues_into_phrase_stage():
    records = []
    for level in range(1, 8):
        records += [word_round(level, 90, minutes=2 * level), word_round(level, 90, minutes=2 * level + 1)]
    state = word_level_state(records)
    assert state["level"] == 8 and state["in_phrase_stage"]
    assert state["exercise_id"] == "words-phrases"
    assert state["progress_text"].startswith("Phrase stage 1 of 3")


def test_word_rounds_do_not_change_the_reading_level():
    words = [word_round(1, 95, minutes=m) for m in range(1, 7)]
    assert level_state(words)["level"] == "beginner"
    reads = [reading("beginner", 90, minutes=1), reading("beginner", 90, minutes=2)]
    assert word_level_state(reads)["level"] == 1
    mixed = sorted(words + reads, key=lambda r: r["completed_at"])
    assert level_state(mixed)["level"] == level_state(reads)["level"]


def test_plan_includes_current_word_level():
    records = [word_round(1, 90, minutes=1), word_round(1, 90, minutes=2)]
    plan = recommend_weekly_plan(records)
    word_items = [e for e in plan["exercises"] if e["source"] == "words"]
    assert [e["id"] for e in word_items] == ["words-2"]
    # Word exercises are placed by their ladder, never picked by the bandit.
    assert all(e["type"] != "words" for e in plan["exercises"] if e["source"] == "bandit")


def test_word_badges():
    from app.therapy.adaptive import earned_badges
    records = [word_round(1, 90, minutes=1)]
    earned = {b["id"] for b in earned_badges(records, level_state(records), 0, 0) if b["earned"]}
    assert "first_words" in earned and "word_master" not in earned


def test_word_level_leads_the_plan_for_a_child_who_only_does_words():
    records = [word_round(1, 90, minutes=1)]
    assert recommend_weekly_plan(records)["exercises"][0]["id"] == "words-2"
    # Once reading starts, reading keeps first place and words are added after.
    records.append(reading("beginner", 70, minutes=2))
    plan = recommend_weekly_plan(records)["exercises"]
    assert plan[0]["id"] == "reading-beginner" and plan[-1]["id"] == "words-2"
