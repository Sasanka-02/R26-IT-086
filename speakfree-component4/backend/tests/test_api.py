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
    # One strong reading unlocks the next level.
    assert second["level"]["level"] == "intermediate"
    assert any((r["level_message"] or "").startswith("Level up") for r in (first, second))

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


def test_word_round_saves_and_climbs_the_ladder(client):
    h = signup(client, "kid@x.com", name="Nethmi")
    exercises = client.get("/api/v1/therapy/exercises/user/kid@x.com", headers=h).json()
    by_id = {e["id"]: e for e in exercises["exercises"]}
    assert not by_id["words-1"]["locked"] and by_id["words-2"]["locked"]
    assert not by_id["words-sri-lanka"]["locked"]
    assert len(by_id["words-1"]["words"]) == 10 and by_id["words-1"]["words"][0]["emoji"]

    first = save_result(client, h, "kid@x.com", exercise_id="words-1", duration_seconds=50,
                        speaking_ratio=None, words_correct=9, words_total=10)
    assert first["record"]["exercise_type"] == "words" and first["record"]["word_level"] == 1
    # One good round unlocks the next word level.
    assert first["word_level"]["level"] == 2 and "Level up" in first["level_message"]
    assert first["level"]["level"] == "beginner"  # reading untouched

    progress = client.get("/api/v1/therapy/progress/kid@x.com", headers=h).json()
    assert progress["word_level"]["level"] == 2
    assert any(t["type"] == "words" for t in progress["by_type"])
    plan = client.get("/api/v1/therapy/plan/kid@x.com", headers=h).json()
    assert any(e["id"] == "words-2" and e["source"] == "words" for e in plan["exercises"])

    bad = client.post("/api/v1/therapy/results", headers=h, json={
        "user_id": "kid@x.com", "exercise_id": "words-1", "words_correct": 11, "words_total": 10})
    assert bad.status_code == 400


def test_student_is_notified_of_shared_therapist_notes(client):
    therapist = signup(client, "dr@x.com", role="therapist", name="Dr Silva")
    student = signup(client, "a@x.com", name="Amal")
    other = signup(client, "b@x.com")
    url = "/api/v1/therapy/notes/a@x.com"
    assert client.get(url, headers=student).json() == {"notes": [], "unread": 0}

    client.post("/api/v1/therapist/students/a@x.com/notes", json={"text": "Great progress on soft starts!"},
                headers=therapist)
    client.post("/api/v1/therapist/students/a@x.com/notes",
                json={"text": "Private: check anxiety next session", "shared": False}, headers=therapist)
    seen = client.get(url, headers=student).json()
    assert seen["unread"] == 1 and len(seen["notes"]) == 1  # the private note is not shown
    assert seen["notes"][0]["text"] == "Great progress on soft starts!"
    assert seen["notes"][0]["by_name"] == "Dr Silva" and seen["notes"][0]["unread"]

    # A therapist opening the notes doesn't clear the student's notification.
    client.post(url + "/read", headers=therapist)
    assert client.get(url, headers=student).json()["unread"] == 1
    read = client.post(url + "/read", headers=student).json()
    assert read["unread"] == 0 and not read["notes"][0]["unread"]

    client.post("/api/v1/therapist/students/a@x.com/notes", json={"text": "Try level 2 this week"}, headers=therapist)
    assert client.get(url, headers=student).json()["unread"] == 1
    assert client.get(url, headers=other).status_code == 403


def test_pilot_study_compares_first_and_last_week(client, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.therapy import pilot, progress_store

    therapist = signup(client, "dr@x.com", role="therapist")
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    def rec(day, score):
        return {"id": f"{day}-{score}", "completed_at": (start + timedelta(days=day)).isoformat(),
                "exercise_type": "reading", "score": score, "speaking_ratio": 0.6, "long_pauses": 1}
    data = {
        "a@x.com": [rec(0, 50), rec(1, 54), rec(12, 70), rec(13, 74)],   # +20
        "b@x.com": [rec(0, 60), rec(2, 60), rec(11, 66), rec(12, 64)],   # +5
        "c@x.com": [rec(0, 70), rec(1, 72), rec(10, 68), rec(12, 70)],   # -2
        "d@x.com": [rec(0, 40), rec(1, 45)],                              # too short
        "kid@demo.local": [rec(0, 10), rec(1, 10), rec(12, 99), rec(13, 99)],  # synthetic: excluded
    }
    monkeypatch.setattr(progress_store, "all_records", lambda: data)
    monkeypatch.setattr(pilot, "all_records", lambda: data)

    report = client.get("/api/v1/therapist/evidence", headers=therapist).json()["pilot"]
    s = report["summary"]
    assert s["participants"] == 3 and s["not_yet_included"] == 1
    assert s["mean_change"] == round((20 + 5 - 2) / 3, 1)
    assert s["improved"] == 2 and s["worsened"] == 1
    assert s["sign_test_p"] == 1.0  # 2 vs 1 is nowhere near significant
    assert s["ci95"][0] < s["mean_change"] < s["ci95"][1]
    assert all(not p["student"].endswith("@demo.local") for p in report["participants"])
    sheet = client.get("/api/v1/therapist/evidence/pilot.csv", headers=therapist)
    assert sheet.status_code == 200 and "first_week_score" in sheet.text.splitlines()[0]


def test_sign_test_exact_values():
    from app.therapy.pilot import sign_test_p
    assert sign_test_p(8, 0) == round(2 / 2**8, 3)  # 8 of 8 improved: p ≈ 0.008
    assert sign_test_p(0, 0) is None


def test_second_rater_and_heard_audio_are_kept(client):
    therapist = signup(client, "dr@x.com", role="therapist")
    student = signup(client, "a@x.com")
    rec = save_result(client, student, "a@x.com")["record"]
    url = f"/api/v1/therapist/students/a@x.com/records/{rec['id']}/rating"
    client.put(url, json={"rating": 4, "heard_audio": True}, headers=therapist)
    client.put(url, json={"rating": 3, "rater": "Ms Perera", "heard_audio": True}, headers=therapist)
    detail = client.get("/api/v1/therapist/students/a@x.com", headers=therapist).json()
    reviews = detail["records"][0]["expert_reviews"]
    assert [r["rating"] for r in reviews] == [4, 3]
    assert reviews[1]["by"] == "Ms Perera (via dr@x.com)" and all(r["heard_audio"] for r in reviews)
    v = client.get("/api/v1/therapist/evidence", headers=therapist).json()["scoring"]["validation_by_source"]
    assert v["clinician"] is None or v["clinician"]["n_heard_audio"] == 1
