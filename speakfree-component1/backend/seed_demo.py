"""
Demo data for the viva: students of different ages, each with a completed screening and a short
practice history, so the therapy plan visibly differs by age bracket.

    python seed_demo.py

Each screening runs through the real platform API and the real C1 -> C2 -> C3 -> C4 pipeline;
only Whisper is replaced by a stub transcript (no audio is needed). The screening is then dated a
week back and practice attempts are added day by day, always on the student's CURRENT bracket,
so the adaptive ladder moves exactly as it would in real use.

Idempotent: accounts that already exist are skipped. Every demo account uses DEMO_PASSWORD.
Run `python seed.py` first (the task library) - this script does it for you if it is empty.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

import main
from age_brackets import bracket_for_age
from config import settings
from database import Patient, PipelineRun, ScreeningSession, SessionLocal, TherapyAttempt, TherapyProfile, User, run_migrations
from seed import seed

DEMO_PASSWORD = "Demo@1234"
DOMAIN = "demo.speakfree.lk"

# history: one practice attempt per step - "strong" (score 75+), "ok", or "hard" (difficult)
DEMO_STUDENTS = [
    {"key": "kavi", "name": "Kavi Perera", "age": 7, "history": ["ok", "strong", "strong", "ok"]},
    {"key": "nethmi", "name": "Nethmi Silva", "age": 10, "history": ["ok", "strong"]},
    {"key": "ravindu", "name": "Ravindu Fernando", "age": 15, "history": ["strong", "hard", "hard", "ok"]},
    {"key": "dilini", "name": "Dilini Jayasuriya", "age": 19, "history": ["ok", "strong", "ok"]},
    {"key": "suresh", "name": "Suresh Wickramasinghe", "age": 35, "history": ["ok", "ok", "strong"]},
]
NO_AGE_STUDENT = {"key": "ama", "name": "Ama Rajapaksa"}  # older account without an age -> "How old are you?" screen

ATTEMPT = {
    "strong": {"duration_seconds": 70, "speaking_ratio": 0.64, "long_pauses": 1, "self_rating": "ok"},
    "ok": {"duration_seconds": 50, "speaking_ratio": 0.5, "long_pauses": 2, "self_rating": "ok"},
    "hard": {"duration_seconds": 30, "speaking_ratio": 0.3, "long_pauses": 1, "self_rating": "hard"},
}
TASK_ROTATION = ["reading", "picture", "conversation"]
SAMPLE = Path(__file__).resolve().parents[2] / "speakfree-component2" / "backend" / "samples" / "component1_output_example.json"


def email(key: str) -> str:
    return f"{key}@{DOMAIN}"


def stub_pipeline(path, task_type, reference_text, keywords, age_bracket):
    """Component 1 result without Whisper: the Component 2 sample transcript with realistic word timings."""
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    words = [{**w, "index": i, "duration": w["end"] - w["start"], "confidence_percent": w["confidence"] * 100,
              "level": "high", "whisper_word_probability": w["confidence"],
              "tokens": [{"token": t["text"], "token_id": 1, "logprob": -0.1, "probability": t["probability"]}
                         for t in w["tokens"]]}
             for i, w in enumerate(sample["word_segments"])]
    feats = {"duration_sec": 6.0, "analysed_duration_sec": 6.0, "speech_duration_sec": 5.0, "speech_ratio": 0.8,
             "words_per_minute": 110.0, "articulation_rate_syll_per_sec": 4.0, "pause_rate_per_min": 6.0,
             "longest_pause_sec": 0.6, "snr_db": 28.0, "pause_count": 1}
    return {
        "transcript": sample["transcript"], "reference_text": reference_text, "overall_confidence_percent": 81.25,
        "dysfluency_threshold": 0.6, "asr_accuracy_percent": 85.0, "asr_score_basis": "overall_confidence",
        "fluency_score": 78.0, "pronunciation_score": 84.0, "articulation_score": 84.0,
        "articulation_score_source": "component1_proxy", "overall_speech_score": 82.0, "mean_word_confidence": 0.85,
        "dysfluency_candidate_count": 2, "dysfluency_ratio": 0.18, "word_accuracy_percent": None, "wer": None,
        "content_coverage_percent": None, "score_components": {},
        "screening_indicator": {"severity_hint": 2, "label": "Mild concern", "risk": "low-moderate", "note": ""},
        "phoneme_findings": [], "low_confidence_regions": [], "word_segments": words, "pauses": [],
        "acoustic_features": feats, "segments": [], "preprocessing": {}, "waveform_peaks": [],
        "model": {"asr": "demo-stub", "device": "cpu", "token_count": 11, "verbatim_prompt": True, "rejected_segments": []},
        "model_features": {"acoustic_biomarker_windows": []},
        "processing_time_ms": 1,
    }


def register(client: TestClient, student: dict) -> tuple[dict, str]:
    r = client.post("/api/v1/auth/register", json={
        "role": "patient", "full_name": student["name"], "email": email(student["key"]), "password": DEMO_PASSWORD,
        "age": student["age"], "guardian_consent": student["age"] < 18, "consent": True,
    })
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]["patients"][0]["id"]


def screen(client: TestClient, h: dict, pid: str) -> str:
    tasks = client.get(f"/api/v1/tasks?patient_id={pid}", headers=h).json()
    session_id = str(uuid.uuid4())
    for task_id, ttype in ((tasks["tasks"]["reading"]["id"], "reading"), (tasks["tasks"]["picture"]["id"], "picture"),
                           (tasks["tasks"]["scenario"]["id"], "scenario"), (tasks["tasks"]["questions"]["items"][0]["id"], "questions")):
        client.post("/api/v1/analyze", headers=h, files={"audio": ("demo.wav", b"\x00" * 2048, "audio/wav")},
                    data={"session_id": session_id, "patient_id": pid, "age_bracket": str(tasks["age_bracket"]["id"]),
                          "task_type": ttype, "task_id": task_id}).raise_for_status()
    client.post(f"/api/v1/sessions/{session_id}/finalize", headers=h, json={"patient_id": pid}).raise_for_status()
    return session_id


def backdate_and_practise(db, pid: str, session_id: str, history: list[str], days_ago: int = 7) -> dict:
    """Move the screening a week back, then add one practice attempt per day on the current bracket."""
    from component4 import build_attempt
    from component4.adaptive import learner_bracket
    from integration.routes import _learner

    t0 = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=days_ago)
    for row in (db.get(ScreeningSession, session_id), db.get(PipelineRun, session_id)):
        if row is not None:
            row.created_at = t0
    profile_row = db.scalar(select(TherapyProfile).where(TherapyProfile.session_id == session_id))
    profile = json.loads(profile_row.profile_json)
    profile["created_at"] = t0.isoformat(timespec="seconds")
    profile_row.created_at, profile_row.profile_json = t0, json.dumps(profile)

    learner = _learner(db, db.get(Patient, pid))
    records: list[dict] = []
    for i, kind in enumerate(history):
        bracket = learner_bracket(profile, records, learner)["bracket"]
        exercise_id = f"b{bracket}-{TASK_ROTATION[i % 3]}"
        record = build_attempt(profile, {"exercise_id": exercise_id, **ATTEMPT[kind]})
        when = t0 + timedelta(days=i + 1, hours=16)
        record["completed_at"] = when.isoformat(timespec="seconds")
        records.append(record)
        db.add(TherapyAttempt(patient_id=pid, exercise_id=exercise_id, exercise_type=record["exercise_type"],
                              score=record["score"], record_json=json.dumps(record), completed_at=when))
    db.commit()
    state = learner_bracket(profile, records, learner)
    return {"severity": profile.get("severity_level"), "start": state["start_bracket"], "now": state["bracket"],
            "text": state["dashboard_text"]}


def add_student_without_age(db) -> bool:
    if db.scalar(select(User).where(User.email == email(NO_AGE_STUDENT["key"]))):
        return False
    user = User(email=email(NO_AGE_STUDENT["key"]), full_name=NO_AGE_STUDENT["name"], role="patient",
                password_hash=main.hash_password(DEMO_PASSWORD), consent_given_at=datetime.now(timezone.utc))
    db.add(user)
    db.flush()
    db.add(Patient(owner_user_id=user.id, full_name=user.full_name, is_self=True))  # no date of birth, no age
    db.commit()
    return True


def main_() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # age labels use en dashes (Windows consoles)
    if settings.auto_migrate:
        run_migrations()
    with SessionLocal() as db:
        seed(db)
    main.run_pipeline = stub_pipeline  # no Whisper / audio for demo screenings
    client = TestClient(main.app)

    print(f"Demo students (password for all: {DEMO_PASSWORD})")
    with SessionLocal() as db:
        for s in DEMO_STUDENTS:
            if db.scalar(select(User).where(User.email == email(s["key"]))):
                print(f"  {email(s['key']):<28} already exists - skipped")
                continue
            h, pid = register(client, s)
            session_id = screen(client, h, pid)
            db.expire_all()
            info = backdate_and_practise(db, pid, session_id, s["history"])
            print(f"  {email(s['key']):<28} age {s['age']:>2} -> bracket {bracket_for_age(s['age'])} · "
                  f"C3 severity {info['severity']} · start L{info['start']} · now L{info['now']}  | {info['text']}")
        if add_student_without_age(db):
            print(f"  {email(NO_AGE_STUDENT['key']):<28} no age yet -> sees the one-time 'How old are you?' screen")


if __name__ == "__main__":
    main_()
