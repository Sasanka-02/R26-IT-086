from datetime import datetime, timedelta, timezone

from app.therapy.adaptive import level_state, personal_target_wpm
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


def test_two_strong_readings_level_up():
    records = [reading("beginner", 90, minutes=1), reading("beginner", 85, minutes=2)]
    assert level_state(records)["level"] == "intermediate"


def test_strong_streak_broken_by_average_attempt():
    records = [reading("beginner", 90, minutes=1), reading("beginner", 60, minutes=2),
               reading("beginner", 90, minutes=3)]
    assert level_state(records)["level"] == "beginner"


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
