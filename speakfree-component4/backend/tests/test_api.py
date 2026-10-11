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
        "email": "dr@x.com", "name": "Dr", "password": "secret123", "role": "therapist", "invite_code": "guess"})
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
