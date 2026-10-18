"""
Database / API tests: login verification, ownership, age-based task delivery, rotation,
analysis bookkeeping and the clinician task library.

Runs against a temporary SQLite database built with the real Alembic migration (see conftest.py),
seeded with seed.py. Whisper is never loaded: run_pipeline is replaced by a stub.
"""
import os
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
from auth import INVALID_CREDENTIALS
from config import settings
from database import Analysis, AssessmentTask, SessionLocal, TaskAttempt, User, run_migrations, utcnow
from seed import seed

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # signature is what the upload validation checks


@pytest.fixture(scope="module")
def client():
    run_migrations()  # real migration 0001 on the temp DB from conftest.py
    with SessionLocal() as db:
        report = seed(db)
        assert len(report.inserted) + len(report.skipped) == 84  # other test modules may have seeded first
        assert len(seed(db).inserted) == 0  # idempotent: a second run inserts nothing
    return TestClient(main.app)  # no `with`: lifespan (startup migration) is not needed here


# --------------------------------------------------------------------------- helpers
def dob_for_age(age: int) -> str:
    today = date.today()
    try:
        birthday = today.replace(year=today.year - age)
    except ValueError:  # 29 February
        birthday = today.replace(year=today.year - age, day=28)
    return (birthday - timedelta(days=30)).isoformat()


def register(client, role="patient", age=11, password="password123", email=None):
    email = email or f"{role}-{uuid.uuid4().hex[:8]}@example.com"
    body = {"role": role, "full_name": f"Test {role.title()}", "email": email, "password": password, "consent": True,
            "guardian_consent": True}
    if role == "patient":
        body["date_of_birth"] = dob_for_age(age)
    elif role == "guardian":
        body |= {"child_full_name": "Test Child", "child_date_of_birth": dob_for_age(age)}
    r = client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    return {"email": email, "token": data["access_token"], "user": data["user"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"}}


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def fake_result(captured: dict):
    def run_pipeline(path, task_type, reference_text, keywords, age_bracket):
        captured.update(task_type=task_type, reference_text=reference_text, keywords=keywords)
        f = {"duration_sec": 5.0, "analysed_duration_sec": 5.0, "speech_duration_sec": 4.0, "speech_ratio": 0.8}
        return {
            "transcript": "hello world", "reference_text": reference_text, "overall_confidence_percent": 90.0,
            "dysfluency_threshold": 0.6, "asr_accuracy_percent": 90.0, "asr_score_basis": "overall_confidence",
            "fluency_score": 80.0, "pronunciation_score": 85.0, "articulation_score": 84.0,
            "articulation_score_source": "component1_proxy", "overall_speech_score": 85.0, "mean_word_confidence": 0.9,
            "dysfluency_candidate_count": 0, "dysfluency_ratio": 0.0, "word_accuracy_percent": None, "wer": None,
            "content_coverage_percent": None, "score_components": {},
            "screening_indicator": {"severity_hint": 1, "label": "Typical range", "risk": "low", "note": ""},
            "phoneme_findings": [], "low_confidence_regions": [], "word_segments": [], "pauses": [],
            "acoustic_features": f, "segments": [], "preprocessing": {}, "waveform_peaks": [],
            "model": {"asr": "stub", "device": "cpu", "token_count": 2, "verbatim_prompt": True, "rejected_segments": []},
            "processing_time_ms": 1,
        }
    return run_pipeline


def analyze(client, account, task_id, task_type, bracket):
    return client.post(
        "/api/v1/analyze",
        headers=account["headers"],
        data={"session_id": str(uuid.uuid4()), "patient_id": account["user"]["patients"][0]["id"],
              "age_bracket": str(bracket), "task_type": task_type, "task_id": task_id},
        files={"audio": ("rec.wav", b"\x00" * 2048, "audio/wav")},
    )


# --------------------------------------------------------------------------- login verification
def test_register_and_login(client):
    acc = register(client, age=11)
    assert acc["user"]["patients"][0]["age_bracket"]["id"] == 3

    r = login(client, acc["email"], "password123")
    assert r.status_code == 200 and r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == acc["email"]
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=acc["email"]).one()
        assert user.last_login_at is not None and user.failed_logins == 0


def test_register_server_side_validation(client):
    acc = register(client)
    dup = client.post("/api/v1/auth/register", json={"role": "patient", "full_name": "Dup", "email": acc["email"],
                                                     "password": "password123", "date_of_birth": dob_for_age(10), "consent": True})
    assert dup.status_code == 409
    base = {"full_name": "X Y", "email": f"v-{uuid.uuid4().hex[:6]}@example.com", "consent": True}
    cases = [
        {**base, "role": "patient", "password": "short", "date_of_birth": dob_for_age(10)},   # password < 8
        {**base, "role": "patient", "password": "password123"},                               # no DOB
        {**base, "role": "patient", "password": "password123", "date_of_birth": dob_for_age(5)},   # too young
        {**base, "role": "patient", "password": "password123", "date_of_birth": dob_for_age(101)},  # too old
        {**base, "role": "guardian", "password": "password123", "child_full_name": "Kid"},    # no child DOB
    ]
    for body in cases:
        assert client.post("/api/v1/auth/register", json=body).status_code == 422, body


def test_unknown_email_and_wrong_password_give_identical_401(client):
    acc = register(client)
    unknown = login(client, "nobody-" + acc["email"], "password123")
    wrong = login(client, acc["email"], "wrong-password")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": INVALID_CREDENTIALS}


def test_five_wrong_passwords_lock_the_account(client):
    acc = register(client)
    for _ in range(settings.max_failed_logins - 1):
        assert login(client, acc["email"], "nope-nope").status_code == 401
    locked = login(client, acc["email"], "nope-nope")
    assert locked.status_code == 423
    assert locked.json()["detail"].startswith("Account locked, try again in 15 minutes")
    # even the correct password is refused while locked
    assert login(client, acc["email"], "password123").status_code == 423

    # once the lock has expired the correct password works and the counter is reset
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=acc["email"]).one()
        user.locked_until = utcnow() - timedelta(seconds=1)
        db.commit()
    assert login(client, acc["email"], "password123").status_code == 200
    with SessionLocal() as db:
        user = db.query(User).filter_by(email=acc["email"]).one()
        assert user.failed_logins == 0 and user.locked_until is None


# --------------------------------------------------------------------------- ownership
def test_user_cannot_access_another_users_patient(client, monkeypatch):
    a, b = register(client), register(client)
    a_patient = a["user"]["patients"][0]["id"]
    monkeypatch.setattr(main, "run_pipeline", fake_result({}))
    tasks = client.get(f"/api/v1/tasks?patient_id={a_patient}", headers=a["headers"]).json()["tasks"]
    analysis_id = analyze(client, a, tasks["picture"]["id"], "picture", 3).json()["analysis_id"]

    assert client.get(f"/api/v1/tasks?patient_id={a_patient}", headers=b["headers"]).status_code == 404
    assert client.get(f"/api/v1/patients/{a_patient}/history", headers=b["headers"]).status_code == 404
    assert client.get(f"/api/v1/results/{analysis_id}", headers=b["headers"]).status_code == 404
    stolen = {**b, "user": {"patients": [{"id": a_patient}]}}
    assert analyze(client, stolen, tasks["picture"]["id"], "picture", 3).status_code == 404
    assert client.get(f"/api/v1/tasks?patient_id={a_patient}").status_code == 401  # no token


# --------------------------------------------------------------------------- age-based delivery
@pytest.mark.parametrize("age,bracket", [(7, 1), (11, 3), (19, 7)])
def test_age_selects_bracket_tasks(client, age, bracket):
    acc = register(client, age=age)
    body = client.get(f"/api/v1/tasks?patient_id={acc['user']['patients'][0]['id']}", headers=acc["headers"]).json()
    assert body["age"] == age and body["age_bracket"]["id"] == bracket
    tasks = body["tasks"]
    for key in ("reading", "picture", "scenario"):
        assert tasks[key]["id"].startswith(f"b{bracket}-"), tasks[key]["id"]
    assert len(tasks["questions"]["items"]) == 3
    assert all(q["id"].startswith(f"b{bracket}-q-") for q in tasks["questions"]["items"])
    assert "image_url" in tasks["picture"] and "visual" in tasks["picture"]
    assert tasks["reading"]["text"] and tasks["scenario"]["prompt"]


def test_guardian_child_gets_child_bracket(client):
    acc = register(client, role="guardian", age=9)
    body = client.get(f"/api/v1/tasks?patient_id={acc['user']['patients'][0]['id']}", headers=acc["headers"]).json()
    assert body["age_bracket"]["id"] == 2


def test_rotation_prefers_unattempted_tasks(client):
    acc = register(client, age=11)
    pid = acc["user"]["patients"][0]["id"]
    with SessionLocal() as db:
        for task_id in ("b3-pic-1", "b3-q-1", "b3-q-2", "b3-scn-1"):
            db.add(TaskAttempt(patient_id=pid, task_id=task_id))
        db.commit()
    tasks = client.get(f"/api/v1/tasks?patient_id={pid}", headers=acc["headers"]).json()["tasks"]
    # two active pictures / scenarios per bracket (custom_tasks.py); the third starter task is switched off
    assert tasks["picture"]["id"] == "b3-pic-2"
    assert tasks["scenario"]["id"] == "b3-scn-2"
    assert [q["id"] for q in tasks["questions"]["items"]] == ["b3-q-3", "b3-q-4", "b3-q-5"]
    # stable across repeated requests until a new attempt is made
    again = client.get(f"/api/v1/tasks?patient_id={pid}", headers=acc["headers"]).json()["tasks"]
    assert again == tasks


def test_analyze_uses_db_task_and_records_attempt(client, monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(main, "run_pipeline", fake_result(captured))
    acc = register(client, age=11)
    pid = acc["user"]["patients"][0]["id"]

    r = analyze(client, acc, "b3-read-1", "reading", 3)
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        reading = db.get(AssessmentTask, "b3-read-1")
        assert captured["reference_text"] == reading.content_text  # WER reference comes from the DB
        analysis = db.get(Analysis, r.json()["analysis_id"])
        assert analysis.task_id == "b3-read-1"
        attempt = db.query(TaskAttempt).filter_by(patient_id=pid).one()
        assert attempt.task_id == "b3-read-1" and attempt.analysis_id == analysis.id

    r = analyze(client, acc, "b3-pic-1", "picture", 3)
    assert r.status_code == 200 and captured["keywords"] and captured["reference_text"] is None

    assert analyze(client, acc, "does-not-exist", "picture", 3).status_code == 422
    assert analyze(client, acc, "b3-pic-1", "scenario", 3).status_code == 422  # type mismatch


# --------------------------------------------------------------------------- clinician task library
def test_admin_endpoints_are_clinician_only(client):
    for role in ("patient", "guardian"):
        acc = register(client, role=role)
        assert client.get("/api/v1/admin/tasks", headers=acc["headers"]).status_code == 403
        assert client.post("/api/v1/admin/tasks", headers=acc["headers"], data={
            "age_bracket": "1", "task_type": "picture", "title": "x", "instructions": "x", "content_text": "x"}).status_code == 403
        assert client.patch("/api/v1/admin/tasks/b1-pic-1", headers=acc["headers"], data={"is_active": "false"}).status_code == 403
    assert client.get("/api/v1/admin/tasks").status_code == 401


def test_clinician_manages_tasks_with_images(client):
    doc = register(client, role="clinician")
    h = doc["headers"]

    listed = client.get("/api/v1/admin/tasks?age_bracket=5&task_type=picture", headers=h).json()
    assert [t["id"] for t in listed] == ["b5-pic-1", "b5-pic-2", "b5-pic-3"]

    form = {"age_bracket": "5", "task_type": "picture", "title": "The Library", "instructions": "Describe the scene.",
            "content_text": "Students studying in a library", "keywords": "library, books, quiet", "max_seconds": "90"}
    created = client.post("/api/v1/admin/tasks", headers=h, data=form, files={"image": ("lib.png", PNG, "image/png")})
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["id"] == "b5-pic-4" and task["keywords"] == ["library", "books", "quiet"]
    assert task["image_path"] == "tasks/b5-pic-4.png" and task["created_by_user_id"] == doc["user"]["id"]
    assert os.path.isfile(os.path.join(settings.static_dir, "tasks", "b5-pic-4.png"))
    served = client.get(task["image_url"].replace("http://testserver", ""))
    assert served.status_code == 200 and served.content == PNG

    # invalid uploads
    bad_sig = client.post("/api/v1/admin/tasks", headers=h, data=form, files={"image": ("fake.png", b"GIF89a" + b"0" * 50, "image/png")})
    assert bad_sig.status_code == 422
    gif = client.post("/api/v1/admin/tasks", headers=h, data=form, files={"image": ("a.gif", b"GIF89a" + b"0" * 50, "image/gif")})
    assert gif.status_code == 422
    too_big = PNG + b"\x00" * (settings.max_image_mb * 1024 * 1024)
    big = client.post("/api/v1/admin/tasks", headers=h, data=form, files={"image": ("big.png", too_big, "image/png")})
    assert big.status_code == 413

    # a 14-year-old who has attempted the three seeded pictures is offered the new one…
    kid = register(client, age=14)
    pid = kid["user"]["patients"][0]["id"]
    with SessionLocal() as db:
        for t in ("b5-pic-1", "b5-pic-2", "b5-pic-3"):
            db.add(TaskAttempt(patient_id=pid, task_id=t))
        db.commit()
    picture = client.get(f"/api/v1/tasks?patient_id={pid}", headers=kid["headers"]).json()["tasks"]["picture"]
    assert picture["id"] == "b5-pic-4" and picture["image_url"].endswith("/static/tasks/b5-pic-4.png")

    # …until a clinician deactivates it
    patched = client.patch("/api/v1/admin/tasks/b5-pic-4", headers=h, data={"is_active": "false", "title": "The Old Library"})
    assert patched.status_code == 200 and patched.json()["is_active"] is False and patched.json()["title"] == "The Old Library"
    picture = client.get(f"/api/v1/tasks?patient_id={pid}", headers=kid["headers"]).json()["tasks"]["picture"]
    assert picture["id"] != "b5-pic-4"
    active_only = client.get("/api/v1/admin/tasks?age_bracket=5&task_type=picture&include_inactive=false", headers=h).json()
    assert "b5-pic-4" not in [t["id"] for t in active_only]

    # remove the image
    removed = client.patch("/api/v1/admin/tasks/b5-pic-4", headers=h, data={"remove_image": "true"}).json()
    assert removed["image_path"] is None and not os.path.exists(os.path.join(settings.static_dir, "tasks", "b5-pic-4.png"))
    assert client.patch("/api/v1/admin/tasks/nope", headers=h, data={"is_active": "true"}).status_code == 404


# --------------------------------------------------------------------------- admin account & patient directory
def admin_headers(client):
    with SessionLocal() as db:
        main.ensure_admin(db)
    r = login(client, settings.admin_email, settings.admin_password)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "admin" and r.json()["user"]["patients"] == []
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_admin_cannot_be_self_registered(client):
    body = {"role": "admin", "full_name": "Sneaky", "email": f"sneaky-{uuid.uuid4().hex[:6]}@example.com",
            "password": "password123", "consent": True}
    assert client.post("/api/v1/auth/register", json=body).status_code == 422


def test_admin_routes_are_admin_only(client):
    for role in ("patient", "guardian", "clinician"):
        acc = register(client, role=role)
        for path in ("/api/v1/admin/patients", f"/api/v1/admin/patients/{acc['user']['patients'][0]['id'] if acc['user']['patients'] else 'x'}"):
            assert client.get(path, headers=acc["headers"]).status_code == 403, (role, path)
    assert client.get("/api/v1/admin/patients").status_code == 401


def test_admin_sees_every_patient_and_their_sessions(client, monkeypatch):
    monkeypatch.setattr(main, "run_pipeline", fake_result({}))
    owner = register(client, age=11)
    other = register(client, age=11)
    pid = owner["user"]["patients"][0]["id"]
    session_id = str(uuid.uuid4())
    for task_id, ttype in (("b3-pic-1", "picture"), ("b3-q-1", "questions")):
        r = client.post("/api/v1/analyze", headers=owner["headers"], files={"audio": ("rec.wav", b"\x00" * 2048, "audio/wav")},
                        data={"session_id": session_id, "patient_id": pid, "age_bracket": "3", "task_type": ttype, "task_id": task_id})
        assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/sessions/{session_id}/finalize", headers=owner["headers"], json={"patient_id": pid}).status_code == 200

    h = admin_headers(client)
    rows = {r["id"]: r for r in client.get("/api/v1/admin/patients", headers=h).json()}
    assert pid in rows and other["user"]["patients"][0]["id"] in rows       # patients of different accounts
    row = rows[pid]
    assert row["total_sessions"] == 1 and row["latest_severity_hint"] == 1 and row["owner_email"] == owner["email"]
    assert rows[other["user"]["patients"][0]["id"]]["total_sessions"] == 0

    profile = client.get(f"/api/v1/admin/patients/{pid}", headers=h).json()
    assert profile["patient"]["full_name"] and profile["date_of_birth"]
    [sess] = profile["sessions"]
    assert sess["session_id"] == session_id and len(sess["recordings"]) == 2
    assert all(rec["audio_retained"] is False for rec in sess["recordings"])  # privacy rule: no server audio
    assert client.get(f"/api/v1/admin/patients/{pid}/sessions", headers=h).json() == profile["sessions"]

    # admin can open the technical session + word-level results of any patient …
    assert client.get(f"/api/v1/sessions/{session_id}/summary", headers=h).status_code == 200
    assert client.get(f"/api/v1/results/{sess['recordings'][0]['analysis_id']}", headers=h).status_code == 200
    # … but other users still cannot, and the admin cannot add patients
    assert client.get(f"/api/v1/sessions/{session_id}/summary", headers=other["headers"]).status_code == 404
    assert client.post("/api/v1/patients", headers=h, json={"full_name": "X Y", "date_of_birth": dob_for_age(10)}).status_code == 403
    assert client.get("/api/v1/admin/patients/nope", headers=h).status_code == 404
