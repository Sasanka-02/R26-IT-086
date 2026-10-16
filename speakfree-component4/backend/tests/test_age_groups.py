from datetime import datetime, timedelta, timezone

import pytest

from app.therapy.adaptive import level_state, personal_target_wpm
from app.therapy.bandit import recommend_weekly_plan
from app.therapy.exercises import EXERCISE_BANK, exercises_for, get_exercise
from app.therapy.user_store import age_group_for
from tests.conftest import save_result, signup

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def attempt(exercise_id, score, minutes, rating="ok"):
    ex = get_exercise(exercise_id)
    return {"exercise_id": exercise_id, "exercise_type": ex.type.value, "level": ex.level.value if ex.level else None,
            "score": score, "self_rating": rating, "completed_at": (T0 + timedelta(minutes=minutes)).isoformat()}


@pytest.mark.parametrize("age, group", [(6, "child"), (13, "child"), (14, "teen"), (20, "teen"), (21, "adult"), (65, "adult")])
def test_age_group_boundaries(age, group):
    assert age_group_for(age) == group


def test_under_six_is_rejected():
    with pytest.raises(ValueError, match="ages 6 and above"):
        age_group_for(5)


def _signup(client, **extra):
    body = {"email": "kid@x.com", "name": "Kid", "password": "secret123", "role": "student", "consent": True, **extra}
    return client.post("/api/v1/auth/signup", json=body)


def test_signup_rules(client):
    assert _signup(client).status_code == 400  # no age
    too_young = _signup(client, age=5, guardian_consent=True)
    assert too_young.status_code == 400 and "ages 6 and above" in too_young.json()["detail"]
    no_guardian = _signup(client, age=12)
    assert no_guardian.status_code == 400 and "guardian" in no_guardian.json()["detail"]
    ok = _signup(client, age=12, guardian_consent=True)
    assert ok.status_code == 200 and ok.json()["user"]["age_group"] == "child"
    # Adults need no guardian, and therapists aren't asked for an age.
    assert _signup(client, email="a@x.com", age=30).json()["user"]["age_group"] == "adult"
    signup(client, "dr@x.com", role="therapist")


def test_existing_student_sets_age_once(client):
    h = signup(client, "a@x.com", age=30)
    teen = client.put("/api/v1/auth/me/age", json={"age": 16, "guardian_consent": True}, headers=h)
    assert teen.status_code == 200 and teen.json()["age_group"] == "teen"
    assert client.put("/api/v1/auth/me/age", json={"age": 4}, headers=h).status_code == 400


def test_exercise_list_is_filtered_by_age(client):
    child = signup(client, "kid@x.com", age=9)
    adult = signup(client, "a@x.com", age=40)
    kid_ids = {e["id"] for e in client.get("/api/v1/therapy/exercises/user/kid@x.com", headers=child).json()["exercises"]}
    adult_ids = {e["id"] for e in client.get("/api/v1/therapy/exercises/user/a@x.com", headers=adult).json()["exercises"]}
    assert "child-words" in kid_ids and "daf-1" not in kid_ids and "adult-interview-about" not in kid_ids
    assert "adult-interview-about" in adult_ids and "child-words" not in adult_ids and "words-1" not in adult_ids
    for group in ("child", "teen", "adult"):
        levels = {e.level.value for e in exercises_for(group) if e.level}
        assert levels == {"beginner", "intermediate", "advanced"}  # every group has a full ladder


@pytest.mark.parametrize("group", ["child", "teen", "adult"])
def test_plan_only_contains_the_groups_exercises(group):
    plan = recommend_weekly_plan([], {}, age_group=group)
    assert plan["exercises"]
    assert all(group in get_exercise(e["id"]).age_groups for e in plan["exercises"])


def test_assigned_exercises_still_come_first():
    plan = recommend_weekly_plan([], {"assigned": [{"exercise_id": "daf-1"}]}, age_group="child")
    assert plan["exercises"][0]["id"] == "daf-1"  # the therapist's choice wins


def test_levels_are_tracked_per_age_group():
    records = [attempt("child-words", 95, 1), attempt("teen-school", 95, 2)]
    assert level_state(records, age_group="child")["level"] == "intermediate"
    assert level_state(records, age_group="teen")["level"] == "intermediate"
    assert level_state(records, age_group="adult")["level"] == "beginner"  # neither counts for adults
    # A role-play at the teen intermediate level moves a teen up again.
    records.append(attempt("teen-present-self", 95, 3))
    assert level_state(records, age_group="teen")["level"] == "advanced"


def test_reading_speed_suits_the_age_group():
    assert personal_target_wpm(130, "pacing-standard-1", [], "child") == 80
    assert personal_target_wpm(90, "pacing-easy-1", [], "adult") == 120
    assert personal_target_wpm(110, "teen-hobby", [], "teen") == 110


def test_therapist_can_change_the_age_group(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    student = signup(client, "a@x.com", age=13, name="Amal")
    res = client.put("/api/v1/therapist/students/a@x.com/age-group", json={"age_group": "teen"}, headers=therapist)
    assert res.status_code == 200 and res.json()["age_group"] == "teen" and res.json()["age"] == 13
    plan = client.get("/api/v1/therapy/plan/a@x.com", headers=student).json()
    assert plan["age_group"] == "teen"
    bad = client.put("/api/v1/therapist/students/a@x.com/age-group", json={"age_group": "baby"}, headers=therapist)
    assert bad.status_code == 400


def test_assistant_talks_differently_to_each_group(client):
    child = signup(client, "kid@x.com", age=8, name="Nethmi")
    adult = signup(client, "a@x.com", age=40, name="Sunil")
    ask = lambda who, h: client.post("/api/v1/therapy/assistant/chat", headers=h,
                                     json={"user_id": who, "name": "x", "message": "i talk too fast"}).json()
    kid_reply = ask("kid@x.com", child)
    adult_reply = ask("a@x.com", adult)
    assert "🐌" in kid_reply["reply"] and len(kid_reply["reply"]) < len(adult_reply["reply"])
    assert "🐌" not in adult_reply["reply"]
    # Buttons only point at exercises the group can open.
    assert kid_reply["action"]["exercise_id"] == "child-pacing"
    assert adult_reply["action"]["exercise_id"] in {e.id for e in exercises_for("adult")}


def test_kid_badge_titles(client):
    child = signup(client, "kid@x.com", age=9)
    save_result(client, child, "kid@x.com", exercise_id="child-pacing")
    badges = client.get("/api/v1/therapy/progress/kid@x.com", headers=child).json()["badges"]
    assert any(b["title"] == "Super Speaker ⭐" and b["earned"] for b in badges)


def test_every_exercise_has_a_known_age_group():
    assert all(set(ex.age_groups) <= {"child", "teen", "adult"} and ex.age_groups for ex in EXERCISE_BANK)
