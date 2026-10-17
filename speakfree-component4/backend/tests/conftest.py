import logging

import pytest
from fastapi.testclient import TestClient

import app.therapy.appointments as appointments
import app.therapy.audit as audit
import app.therapy.messages as messages
import app.therapy.auth as auth
import app.therapy.cohort_report as cohort_report
import app.therapy.plan_review as plan_review
import app.therapy.recordings as recordings
import app.therapy.privacy as privacy
import app.therapy.progress_store as progress_store
import app.therapy.scoring as scoring
import app.therapy.survey as survey
import app.therapy.therapist_store as therapist_store
import app.therapy.user_store as user_store
from app.main import app

logging.disable(logging.INFO)


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Every test gets its own empty data directory — real data is never touched."""
    monkeypatch.setattr(progress_store, "DATA_FILE", tmp_path / "progress.json")
    monkeypatch.setattr(user_store, "USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(therapist_store, "STORE_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(scoring, "CALIBRATION_FILE", tmp_path / "calibration.json")
    monkeypatch.setattr(auth, "SECRET_FILE", tmp_path / "secret.key")
    monkeypatch.setattr(survey, "SURVEY_FILE", tmp_path / "surveys.json")
    monkeypatch.setattr(plan_review, "REVIEWS_FILE", tmp_path / "plan_reviews.json")
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit_log.jsonl")
    monkeypatch.setattr(messages, "MESSAGES_FILE", tmp_path / "messages.json")
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", tmp_path / "recordings")
    monkeypatch.setattr(appointments, "APPOINTMENTS_FILE", tmp_path / "appointments.json")
    monkeypatch.setattr(auth, "_failed_logins", {})
    monkeypatch.setattr(cohort_report, "_cache", {})
    monkeypatch.setattr(privacy, "budget_ledger", privacy.PrivacyBudgetLedger())
    monkeypatch.setattr(cohort_report, "budget_ledger", privacy.budget_ledger)
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


def signup(client, email, role="student", name="Test User", password="secret123", age=30):
    """Students default to age 30 (adult group); pass age= for a child or teen."""
    body = {"email": email, "name": name, "password": password, "role": role, "consent": True}
    if role == "therapist":
        body["invite_code"] = auth.THERAPIST_INVITE_CODE
    else:
        body["age"] = age
        body["guardian_consent"] = age < 18
    res = client.post("/api/v1/auth/signup", json=body)
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


def save_result(client, headers, email, exercise_id="reading-beginner", **kw):
    body = {
        "user_id": email,
        "exercise_id": exercise_id,
        "duration_seconds": 40,
        "speaking_ratio": 0.75,
        "long_pauses": 0,
        "quiet_warnings": 0,
        "self_rating": "ok",
        **kw,
    }
    res = client.post("/api/v1/therapy/results", json=body, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()
