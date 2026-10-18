"""
Age-bracketed therapy on the platform: age at sign-up (6–100), guardian consent under 18, the
one-time "How old are you?" update, adult screening, different therapy tasks per age, and the
therapist's bracket override / exercise assignment.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

import main
from age_brackets import age_bracket_for, bracket_for_age
from database import Patient, SessionLocal, User, run_migrations
from seed import seed
from tests.test_db import admin_headers, register
from tests.test_integration import fake_pipeline


@pytest.fixture(scope="module")
def client():
    run_migrations()
    with SessionLocal() as db:
        seed(db)
    return TestClient(main.app)


def signup(client, age, role="patient", guardian_consent=None):
    body = {"role": role, "full_name": "Age Tester", "email": f"age-{uuid.uuid4().hex[:8]}@example.com",
            "password": "password123", "consent": True}
    if role == "patient":
        body["age"] = age
    elif role == "guardian":
        body |= {"child_full_name": "Little Tester", "child_age": age}
    if guardian_consent is not None:
        body["guardian_consent"] = guardian_consent
    return client.post("/api/v1/auth/register", json=body)


def headers(r):
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def screen(client, h, pid):
    """Run one screening through the real C1 -> C2 -> C3 -> C4 pipeline (Whisper stubbed)."""
    tasks = client.get(f"/api/v1/tasks?patient_id={pid}", headers=h).json()
    session_id = str(uuid.uuid4())
    picks = [(tasks["tasks"]["picture"]["id"], "picture"), (tasks["tasks"]["scenario"]["id"], "scenario"),
             (tasks["tasks"]["questions"]["items"][0]["id"], "questions")]
    for task_id, ttype in picks:
        r = client.post("/api/v1/analyze", headers=h, files={"audio": ("rec.wav", b"\x00" * 2048, "audio/wav")},
                        data={"session_id": session_id, "patient_id": pid, "age_bracket": str(tasks["age_bracket"]["id"]),
                              "task_type": ttype, "task_id": task_id})
        assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/sessions/{session_id}/finalize", headers=h, json={"patient_id": pid}).status_code == 200
    return tasks


# --------------------------------------------------------------------------- sign-up
def test_platform_uses_the_single_bracket_helper():
    for age in (6, 7, 8, 11, 15, 19, 20, 21, 64):
        assert bracket_for_age(age) == age_bracket_for(age)


def test_under_six_is_rejected(client):
    r = signup(client, 5, guardian_consent=True)
    assert r.status_code == 422 and r.json()["detail"] == "This app is for ages 6 and above"


def test_guardian_consent_required_under_18(client):
    assert signup(client, 12).status_code == 422
    assert signup(client, 12, guardian_consent=False).status_code == 422
    ok = signup(client, 12, guardian_consent=True)
    assert ok.status_code == 201, ok.text
    patient = ok.json()["user"]["patients"][0]
    assert patient["age"] == 12 and patient["age_bracket"]["id"] == 4 and patient["guardian_consent"] is True
    assert signup(client, 9, role="guardian").status_code == 422
    assert signup(client, 9, role="guardian", guardian_consent=True).json()["user"]["patients"][0]["age_bracket"]["id"] == 2


def test_adults_need_no_guardian_and_therapists_no_age(client):
    adult = signup(client, 18)
    assert adult.status_code == 201 and adult.json()["user"]["patients"][0]["age_bracket"]["id"] == 7
    assert signup(client, 35).json()["user"]["patients"][0]["age_bracket"]["id"] == 8
    assert signup(client, 101).status_code == 422
    clinician = client.post("/api/v1/auth/register", json={"role": "clinician", "full_name": "Dr Therapist", "consent": True,
                                                           "email": f"slp-{uuid.uuid4().hex[:6]}@example.com",
                                                           "password": "password123"})
    assert clinician.status_code == 201 and clinician.json()["user"]["patients"] == []


def test_existing_student_without_age_sets_it_once(client):
    acc = register(client, age=10)
    with SessionLocal() as db:  # an account from before age was collected
        user = db.get(User, acc["user"]["id"])
        p = Patient(owner_user_id=user.id, full_name="Old Account", is_self=False)
        db.add(p)
        db.commit()
        pid = p.id
    me = client.get("/api/v1/auth/me", headers=acc["headers"]).json()
    assert next(p for p in me["patients"] if p["id"] == pid)["age"] is None
    bad = client.put("/api/v1/auth/me/age", headers=acc["headers"], json={"age": 4, "patient_id": pid})
    assert bad.status_code == 422 and bad.json()["detail"] == "This app is for ages 6 and above"
    assert client.put("/api/v1/auth/me/age", headers=acc["headers"], json={"age": 14, "patient_id": pid}).status_code == 422
    r = client.put("/api/v1/auth/me/age", headers=acc["headers"], json={"age": 14, "patient_id": pid, "guardian_consent": True})
    assert r.status_code == 200, r.text
    saved = next(p for p in r.json()["patients"] if p["id"] == pid)
    assert saved["age"] == 14 and saved["age_bracket"]["id"] == 5
    # the self record has a date of birth -> its age is not editable here
    assert client.put("/api/v1/auth/me/age", headers=acc["headers"], json={"age": 30}).status_code == 409


# --------------------------------------------------------------------------- therapy by age
def test_different_ages_get_different_tasks(client, monkeypatch):
    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    seen = {}
    for age, bracket in ((7, 1), (15, 5), (35, 8)):
        r = signup(client, age, guardian_consent=True)
        h, pid = headers(r), r.json()["user"]["patients"][0]["id"]
        tasks = screen(client, h, pid)
        assert tasks["therapy_bracket"]["id"] == bracket and tasks["age_bracket"]["id"] == min(bracket, 7)
        plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=h).json()
        assert plan["learner"]["age_bracket"] == bracket
        core = {e["id"] for e in plan["today"] if e["source"] == "bracket"}
        start = plan["level"]["bracket"]
        assert start in (bracket, max(1, bracket - 1))  # severe screening starts one lower
        assert core == {f"b{start}-reading", f"b{start}-picture", f"b{start}-conversation"}
        seen[age] = core
    assert len({frozenset(v) for v in seen.values()}) == 3


def test_therapist_override_and_assignment(client, monkeypatch):
    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    r = signup(client, 11, guardian_consent=True)
    h, pid = headers(r), r.json()["user"]["patients"][0]["id"]
    screen(client, h, pid)
    url = f"/api/v1/admin/patients/{pid}/therapy-settings"
    assert client.patch(url, headers=h, json={"age_bracket_override": 2}).status_code == 403  # patients cannot
    admin = admin_headers(client)
    assert client.patch(url, headers=admin, json={"age_bracket_override": 9}).status_code == 422
    assert client.patch(url, headers=admin, json={"assigned_exercise_ids": ["nope"]}).status_code == 422
    out = client.patch(url, headers=admin, json={"age_bracket_override": 2, "assigned_exercise_ids": ["daf"]}).json()
    assert out["age_bracket_override"] == 2 and out["assigned_exercises"] == ["daf"]

    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=h).json()
    assert plan["level"]["bracket"] == 2 and plan["level"]["override"]
    assert plan["today"][0]["id"] == "daf" and plan["today"][0]["source"] == "therapist"
    monitor = client.get(f"/api/v1/admin/patients/{pid}/therapy", headers=admin).json()
    assert monitor["patient"]["age_bracket"]["id"] == 3 and monitor["patient"]["age_bracket_override"] == 2
    row = next(p for p in client.get("/api/v1/admin/patients", headers=admin).json() if p["id"] == pid)
    assert row["age"] == 11 and row["age_bracket_override"] == 2

    # only the sent field changes; null clears the override
    client.patch(url, headers=admin, json={"age_bracket_override": None})
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=h).json()
    assert not plan["level"]["override"] and plan["today"][0]["id"] == "daf"
