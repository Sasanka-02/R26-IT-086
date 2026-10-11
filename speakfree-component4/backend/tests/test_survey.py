import pytest

from app.therapy import survey

from .conftest import save_result, signup

BEST = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]
WORST = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]
NEUTRAL = [3] * 10


def test_sus_scoring_extremes():
    assert survey.sus_score(BEST) == 100
    assert survey.sus_score(WORST) == 0
    assert survey.sus_score(NEUTRAL) == 50


def test_sus_rejects_bad_answers():
    with pytest.raises(ValueError):
        survey.sus_score([3] * 9)
    with pytest.raises(ValueError):
        survey.sus_score([6] + [3] * 9)


def test_summary_statistics():
    survey.submit("a@x.com", "student", BEST, "Loved it")
    survey.submit("b@x.com", "student", NEUTRAL, None)
    survey.submit("dr@x.com", "therapist", BEST, None)
    result = survey.summary()
    assert result["overall"]["n"] == 3
    assert result["overall"]["mean"] == pytest.approx(83.3, abs=0.1)
    assert result["by_role"]["therapist"]["mean"] == 100
    assert result["comments"][0]["comment"] == "Loved it"


def test_repeat_response_replaces_previous():
    survey.submit("a@x.com", "student", WORST, None)
    survey.submit("a@x.com", "student", BEST, None)
    assert survey.summary()["overall"]["n"] == 1
    assert survey.summary()["overall"]["mean"] == 100


def test_students_invited_after_three_sessions(client):
    student = signup(client, "a@x.com")
    status = client.get("/api/v1/survey/status", headers=student).json()
    assert not status["invite"]
    for _ in range(3):
        save_result(client, student, "a@x.com")
    status = client.get("/api/v1/survey/status", headers=student).json()
    assert status["invite"]
    res = client.post("/api/v1/survey", json={"answers": BEST}, headers=student)
    assert res.json() == {"score": 100.0, "band": "Excellent"}
    assert not client.get("/api/v1/survey/status", headers=student).json()["invite"]


def test_survey_appears_on_evidence_page(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    client.post("/api/v1/survey", json={"answers": NEUTRAL}, headers=therapist)
    usability = client.get("/api/v1/therapist/evidence", headers=therapist).json()["usability"]
    assert usability["overall"]["n"] == 1
    assert usability["benchmark"] == 68
