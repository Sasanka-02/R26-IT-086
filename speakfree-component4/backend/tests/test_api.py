from app.therapy import auth

from .conftest import save_result, signup


def test_password_hashing():
    stored = auth.hash_password("secret123")
    assert "secret123" not in stored
    assert auth.verify_password("secret123", stored)
    assert not auth.verify_password("wrong", stored)


def test_tampered_token_rejected():
    token = auth.issue_token({"email": "a@x.com", "role": "student"})
    body, sig = token.split(".")
    forged = auth._b64(b'{"sub":"a@x.com","role":"therapist","exp":9999999999}')
    assert auth.decode_token(f"{forged}.{sig}") is None
    assert auth.decode_token(token)["role"] == "student"


def test_endpoints_require_login(client):
    assert client.get("/api/v1/therapy/progress/a@x.com").status_code == 401
    assert client.get("/api/v1/therapist/students").status_code == 401


def test_wrong_password(client):
    signup(client, "a@x.com")
    res = client.post("/api/v1/auth/login", json={"email": "a@x.com", "password": "nope"})
    assert res.status_code == 401


def test_student_cannot_read_another_student(client):
    a = signup(client, "a@x.com")
    signup(client, "b@x.com")
    assert client.get("/api/v1/therapy/progress/b@x.com", headers=a).status_code == 403
    assert client.get("/api/v1/therapist/students", headers=a).status_code == 403


def test_therapist_needs_invite_code(client):
    res = client.post("/api/v1/auth/signup", json={
        "email": "dr@x.com", "name": "Dr", "password": "secret123", "role": "therapist", "invite_code": "guess",
        "consent": True})
    assert res.status_code == 403


def test_full_student_and_therapist_flow(client):
    student = signup(client, "amal@x.com", name="Amal Perera")
    therapist = signup(client, "dr@x.com", role="therapist", name="Dr Silva")

    first = save_result(client, student, "amal@x.com", syllables=60, target_wpm=80)
    assert first["breakdown"] and first["measured_wpm"]
    second = save_result(client, student, "amal@x.com")
    assert second["level"]["level"] == "intermediate"
    assert second["level_message"].startswith("Level up")

    progress = client.get("/api/v1/therapy/progress/amal@x.com", headers=student).json()
    assert progress["total_sessions"] == 2
    assert any(b["earned"] for b in progress["badges"])

    students = client.get("/api/v1/therapist/students", headers=therapist).json()
    assert [s["name"] for s in students] == ["Amal Perera"]

    # Therapist steers the plan and rates an attempt.
    client.put("/api/v1/therapist/students/amal@x.com/assigned",
               json={"exercise_ids": ["daf-1"]}, headers=therapist)
    plan = client.get("/api/v1/therapy/plan/amal@x.com", headers=student).json()
    assert plan["exercises"][0]["id"] == "daf-1"

    client.post("/api/v1/therapist/students/amal@x.com/goals",
                json={"metric": "sessions_per_week", "target": 2}, headers=therapist)
    goals = client.get("/api/v1/therapy/progress/amal@x.com", headers=student).json()["goals"]
    assert goals[0]["met"]

    record_id = first["record"]["id"]
    rated = client.put(f"/api/v1/therapist/students/amal@x.com/records/{record_id}/rating",
                       json={"rating": 4}, headers=therapist)
    assert rated.status_code == 200
    assert rated.json()["calibration"]["n_ratings"] == 1

    evidence = client.get("/api/v1/therapist/evidence", headers=therapist).json()
    assert evidence["ratings"][0]["expert_rating"] == 4
    assert evidence["assistant"]["accuracy"] >= 80


def test_cohort_report_is_cached_and_spends_budget_once(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    student = signup(client, "a@x.com")
    save_result(client, student, "a@x.com")
    first = client.get("/api/v1/therapist/cohort-report?epsilon=1.0", headers=therapist).json()
    second = client.get("/api/v1/therapist/cohort-report?epsilon=1.0", headers=therapist).json()
    assert first["by_type"] == second["by_type"]
    assert second["budget"]["epsilon_spent"] == 1.0
    errors = {row["epsilon"]: row["count_error"] for row in first["accuracy"]}
    assert errors[0.25] > errors[5.0]  # stronger privacy -> more noise


def test_plan_review_compare_and_report_card(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    a = signup(client, "a@x.com", name="Amal")
    b = signup(client, "b@x.com", name="Ravi")
    for _ in range(3):
        save_result(client, a, "a@x.com", speaking_ratio=0.9)
    save_result(client, b, "b@x.com", speaking_ratio=0.3, long_pauses=4, self_rating="hard")

    progress = client.get("/api/v1/therapy/progress/a@x.com", headers=a).json()
    card = progress["report_card"]
    assert card["status"] in {"improving", "steady", "needs_support"}
    assert card["headline"] and card["next_step"].startswith("Next:")
    assert progress["level"]["history"][0]["direction"] == "up"

    plan = client.get("/api/v1/therapy/plan/a@x.com", headers=a).json()
    assert plan["why"] and all(ex["explanation"] for ex in plan["exercises"])

    bad = client.post("/api/v1/therapist/students/a@x.com/plan-review", json={"verdict": "maybe"}, headers=therapist)
    assert bad.status_code == 400
    ok = client.post("/api/v1/therapist/students/a@x.com/plan-review",
                     json={"verdict": "appropriate"}, headers=therapist)
    assert ok.status_code == 200 and ok.json()["source"] == "clinician"
    evidence = client.get("/api/v1/therapist/evidence", headers=therapist).json()
    assert evidence["plan_validation"]["clinician"]["appropriate_pct"] == 100

    compare = client.get("/api/v1/therapist/compare", params={"a": "a@x.com", "b": "b@x.com"},
                         headers=therapist).json()
    left, right = compare["students"]
    assert left["level"]["level"] != right["level"]["level"]
    assert left["assistant"]["reply"]

    sheet = client.get("/api/v1/therapist/evidence/ratings.csv", headers=therapist)
    assert sheet.status_code == 200 and sheet.text.startswith("student,")


def test_signup_requires_consent(client):
    res = client.post("/api/v1/auth/signup", json={"email": "a@x.com", "name": "A", "password": "secret123"})
    assert res.status_code == 400


def test_login_is_rate_limited(client):
    signup(client, "a@x.com")
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"email": "a@x.com", "password": "wrong"}).status_code == 401
    blocked = client.post("/api/v1/auth/login", json={"email": "a@x.com", "password": "secret123"})
    assert blocked.status_code == 429


def test_screening_sets_start_level_and_plan(client):
    severe = signup(client, "s@x.com")
    mild = signup(client, "m@x.com")
    res = client.post("/api/v1/therapy/screening", json={"user_id": "s@x.com", "severity": "severe"}, headers=severe)
    assert res.status_code == 200
    assert res.json()["level"]["level"] == "beginner"
    assert any(ex["id"] == "daf-1" for ex in res.json()["plan"]["exercises"])
    res = client.post("/api/v1/therapy/screening", json={"user_id": "m@x.com", "severity": "mild"}, headers=mild)
    assert res.json()["level"]["level"] == "intermediate"
    assert not res.json()["level"]["set_by_therapist"]
    # A student cannot submit a screening for someone else.
    other = client.post("/api/v1/therapy/screening", json={"user_id": "s@x.com", "severity": "mild"}, headers=mild)
    assert other.status_code == 403


def test_disfluency_count_lowers_score(client):
    h = signup(client, "a@x.com")
    clean = save_result(client, h, "a@x.com", syllables=100, disfluencies=0)
    stutter = save_result(client, h, "a@x.com", syllables=100, disfluencies=12)
    assert stutter["score"] < clean["score"]
    assert any(p["feature"] == "pct_ss" for p in stutter["breakdown"])


def test_download_and_delete_my_data(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    h = signup(client, "a@x.com")
    rec = save_result(client, h, "a@x.com")["record"]
    client.put(f"/api/v1/therapist/students/a@x.com/records/{rec['id']}/rating", json={"rating": 4}, headers=therapist)
    data = client.get("/api/v1/auth/me/data", headers=h).json()
    assert len(data["practice_records"]) == 1 and "password_hash" not in data["account"]
    assert client.delete("/api/v1/auth/me", headers=h).status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401
    evidence = client.get("/api/v1/therapist/evidence", headers=therapist).json()
    assert evidence["scoring"]["n_clinician"] == 0
    audit = client.get("/api/v1/therapist/audit", headers=therapist).json()
    assert {"attempt.rated", "account.deleted"} <= {e["action"] for e in audit}
