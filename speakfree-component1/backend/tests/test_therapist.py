"""
Component 4 features carried over from the stand-alone prototype, end to end through the platform:
patient dashboard + plan explanation, word ladder, therapist controls (homework, goals, notes,
ratings, plan review), DAF calibration, privacy / export, usability survey and the evidence pages.
"""
import json

import pytest

from tests.test_db import admin_headers, register
from tests.test_integration import client, screened_patient  # noqa: F401  (fixture re-export)

HIDDEN = ("engine", "severity", "dysarthria", "stuttering", "disorder")


def _attempt(client, acc, pid, exercise_id, **extra):
    body = {"exercise_id": exercise_id, "duration_seconds": 60, "speaking_ratio": 0.8, "syllables": 100,
            "self_rating": "easy", **extra}
    r = client.post(f"/api/v1/therapy/{pid}/attempts", headers=acc["headers"], json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_plan_has_dashboard_explanation_and_word_ladder(client, monkeypatch):
    acc, pid, _ = screened_patient(client, monkeypatch)  # age 11 -> bracket 3 (ages 6-11 get word cards)
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()
    for key in ("dashboard", "why", "homework", "word_level"):
        assert key in plan, key
    assert plan["dashboard"]["report_card"]["label"] == "Getting started"
    assert plan["why"] and plan["word_level"]["level"] == 1
    library = {e["id"]: e for e in plan["library"]}
    assert not library["words-1"]["locked"] and library["words-2"]["locked"]
    assert "teen-present-self" not in library  # role-plays start at ages 12+

    result = _attempt(client, acc, pid, "words-1", speaking_ratio=None, syllables=None, items_total=10, items_clear=10)
    assert result["score"] >= 75 and result["record"]["word_level"] == 1
    assert {b["id"] for b in result["new_badges"]} >= {"first_step", "first_words"}
    result = _attempt(client, acc, pid, "words-1", speaking_ratio=None, syllables=None, items_total=10, items_clear=10)
    assert "Word Level 2" in (result["level_message"] or "")
    plan = result["plan"]
    assert plan["word_level"]["level"] == 2 and plan["dashboard"]["weekly"][0]["sessions"] == 2
    text = json.dumps(plan).lower()
    for hidden in HIDDEN:
        assert hidden not in text, hidden


def test_therapist_controls_reach_the_patient(client, monkeypatch):
    acc, pid, _ = screened_patient(client, monkeypatch)
    h = admin_headers(client)

    # homework: assign -> due date + 2 attempts -> shown to the patient with progress
    assert client.patch(f"/api/v1/admin/patients/{pid}/therapy-settings", headers=h,
                        json={"assigned_exercise_ids": ["pacing-easy"]}).status_code == 200
    r = client.patch(f"/api/v1/admin/patients/{pid}/homework/pacing-easy", headers=h, json={"due": "2030-01-01", "times": 2})
    assert r.status_code == 200 and r.json()["times"] == 2
    assert client.patch(f"/api/v1/admin/patients/{pid}/homework/daf", headers=h, json={"times": 1}).status_code == 404
    _attempt(client, acc, pid, "pacing-easy")
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()
    item = plan["homework"]["items"][0]
    assert item["exercise_id"] == "pacing-easy" and item["done_count"] == 1 and not item["done"] and plan["homework"]["open"] == 1
    assert plan["today"][0]["source"] == "therapist"

    # goals
    g = client.post(f"/api/v1/admin/patients/{pid}/goals", headers=h, json={"metric": "sessions_per_week", "target": 1})
    assert g.status_code == 200
    assert client.post(f"/api/v1/admin/patients/{pid}/goals", headers=h, json={"metric": "nope", "target": 1}).status_code == 422
    goals = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()["goals"]
    mine = next(x for x in goals if x.get("source") == "therapist")
    assert mine["met"] and mine["current"] == 1

    # notes: shared ones reach the patient as unread; private ones never do
    client.post(f"/api/v1/admin/patients/{pid}/notes", headers=h, json={"text": "Great work this week!", "shared": True})
    client.post(f"/api/v1/admin/patients/{pid}/notes", headers=h, json={"text": "Private observation", "shared": False})
    notes = client.get(f"/api/v1/therapy/{pid}/notes", headers=acc["headers"]).json()
    assert notes["unread"] == 1 and [n["text"] for n in notes["notes"]] == ["Great work this week!"]
    assert client.post(f"/api/v1/therapy/{pid}/notes/read", headers=acc["headers"]).json()["unread"] == 0

    # rating + plan review + monitor panel
    therapy = client.get(f"/api/v1/admin/patients/{pid}/therapy", headers=h).json()
    attempt_id = therapy["attempts"][0]["attempt_id"]
    assert client.put(f"/api/v1/admin/attempts/{attempt_id}/rating", headers=h, json={"rating": 4}).status_code == 200
    assert client.post(f"/api/v1/admin/patients/{pid}/plan-review", headers=h,
                       json={"verdict": "appropriate", "note": "Good mix"}).status_code == 200
    therapy = client.get(f"/api/v1/admin/patients/{pid}/therapy", headers=h).json()
    panel = therapy["therapist"]
    assert therapy["attempts"][0]["my_rating"] == 4
    assert len(panel["notes"]) == 2 and panel["plan_reviews"][0]["verdict"] == "appropriate"
    assert panel["homework"][0]["times"] == 2 and panel["goal_rows"]
    assert client.delete(f"/api/v1/admin/patients/{pid}/goals/{g.json()['id']}", headers=h).status_code == 204

    # the patient cannot use therapist controls
    for method, path, body in (("post", f"/api/v1/admin/patients/{pid}/notes", {"text": "x"}),
                               ("post", f"/api/v1/admin/patients/{pid}/goals", {"metric": "average_score", "target": 50}),
                               ("put", f"/api/v1/admin/attempts/{attempt_id}/rating", {"rating": 5})):
        assert getattr(client, method)(path, headers=acc["headers"], json=body).status_code == 403


def test_daf_calibration_privacy_export_and_survey(client, monkeypatch):
    acc, pid, _ = screened_patient(client, monkeypatch)
    trials = [{"delay_ms": d, "stutter_events": s, "speech_rate_wpm": w}
              for d, s, w in ((50, 4, 150), (100, 2, 140), (150, 1, 128), (200, 1, 110), (300, 3, 95))]
    r = client.post(f"/api/v1/therapy/{pid}/daf/calibrate", headers=acc["headers"], json={"trials": trials})
    assert r.status_code == 200 and r.json()["recommended_delay_ms"] == 150
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()
    assert next(e for e in plan["library"] if e["type"] == "daf")["recommended_delay_ms"] == 150

    privacy = client.get(f"/api/v1/therapy/{pid}/privacy", headers=acc["headers"]).json()
    assert privacy["never_stored"] and privacy["cohort_privacy"]["epsilon_threshold"] == 10.0
    export = client.get(f"/api/v1/therapy/{pid}/export", headers=acc["headers"])
    assert export.status_code == 200 and "attachment" in export.headers["content-disposition"]

    status = client.get("/api/v1/survey", headers=acc["headers"]).json()
    assert len(status["items"]) == 10 and not status["invite"]  # fewer than 3 exercises yet
    for _ in range(3):
        _attempt(client, acc, pid, plan["today"][0]["id"])
    assert client.get("/api/v1/survey", headers=acc["headers"]).json()["invite"]
    r = client.post("/api/v1/survey", headers=acc["headers"], json={"answers": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]})
    assert r.json() == {"score": 100.0, "band": "Excellent"}
    after = client.get("/api/v1/survey", headers=acc["headers"]).json()
    assert after["responded"] and not after["invite"]
    assert client.post("/api/v1/survey", headers=acc["headers"], json={"answers": [9] * 10}).status_code == 422


def test_evidence_and_private_cohort_report(client, monkeypatch):
    acc, pid, _ = screened_patient(client, monkeypatch)
    h = admin_headers(client)
    _attempt(client, acc, pid, "pacing-easy")
    attempt_id = client.get(f"/api/v1/admin/patients/{pid}/therapy", headers=h).json()["attempts"][0]["attempt_id"]
    client.put(f"/api/v1/admin/attempts/{attempt_id}/rating", headers=h, json={"rating": 3})

    ev = client.get("/api/v1/admin/evidence", headers=h).json()
    assert ev["agreement"]["n"] >= 1 and ev["agreement"]["current"]["mae"] >= 0
    assert ev["federated"]["status"].startswith("design") and ev["scoring"]["weights"]

    first = client.get("/api/v1/admin/evidence/cohort?epsilon=1.0", headers=h).json()
    again = client.get("/api/v1/admin/evidence/cohort?epsilon=1.0", headers=h).json()
    assert first["mean_score"] == again["mean_score"]  # same data + ε -> same noisy release
    assert again["budget"]["epsilon_spent"] == first["budget"]["epsilon_spent"]  # ...and no double spending
    assert client.get("/api/v1/admin/evidence/cohort?epsilon=0.3", headers=h).status_code == 422
    for path in ("/api/v1/admin/evidence", "/api/v1/admin/evidence/cohort"):
        assert client.get(path, headers=acc["headers"]).status_code == 403


@pytest.mark.parametrize("age,picture", [(14, "picture-teen-canteen"), (25, "picture-adult-market")])
def test_extra_practice_follows_age(client, monkeypatch, age, picture):
    import main
    from tests.test_age_brackets import screen
    from tests.test_integration import fake_pipeline

    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    acc = register(client, age=age)
    pid = acc["user"]["patients"][0]["id"]
    screen(client, acc["headers"], pid)
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()
    ids = {e["id"] for e in plan["library"]}
    types = {e["type"] for e in plan["library"]}
    assert "roleplay" in types and "words" not in types and picture in ids
    assert plan["word_level"] is None
