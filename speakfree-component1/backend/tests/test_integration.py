"""
Integration tests: finalising a screening runs C2 -> C3 -> C4 in the backend, the admin sees every
stage, and the patient sees only a patient-safe therapy plan (no disorder / severity).
Whisper is never loaded: run_pipeline is replaced by a stub that returns realistic word timings.
"""
import json
import uuid
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

import main
from config import settings
from database import SessionLocal, run_migrations
from seed import seed
from tests.test_db import admin_headers, register

SAMPLE = json.loads((Path(__file__).resolve().parents[3] / "speakfree-component2" / "backend" / "samples"
                     / "component1_output_example.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client():
    run_migrations()  # 0001 + 0002 (integration tables) on the shared temp DB
    with SessionLocal() as db:
        seed(db)  # idempotent - test_db.py may already have seeded it
    return TestClient(main.app)


def fake_pipeline(path, task_type, reference_text, keywords, age_bracket):
    words = [{**w, "index": i, "duration": w["end"] - w["start"], "confidence_percent": w["confidence"] * 100,
              "level": "high", "whisper_word_probability": w["confidence"],
              "tokens": [{"token": t["text"], "token_id": 1, "logprob": -0.1, "probability": t["probability"]}
                         for t in w["tokens"]]}
             for i, w in enumerate(SAMPLE["word_segments"])]
    feats = {"duration_sec": 6.0, "analysed_duration_sec": 6.0, "speech_duration_sec": 5.0, "speech_ratio": 0.8,
             "words_per_minute": 110.0, "articulation_rate_syll_per_sec": 4.0, "pause_rate_per_min": 6.0,
             "longest_pause_sec": 0.6, "snr_db": 28.0, "pause_count": 1}
    return {
        "transcript": SAMPLE["transcript"], "reference_text": None, "overall_confidence_percent": 81.25,
        "dysfluency_threshold": 0.6, "asr_accuracy_percent": 85.0, "asr_score_basis": "overall_confidence",
        "fluency_score": 78.0, "pronunciation_score": 84.0, "articulation_score": 84.0,
        "articulation_score_source": "component1_proxy", "overall_speech_score": 82.0, "mean_word_confidence": 0.85,
        "dysfluency_candidate_count": 2, "dysfluency_ratio": 0.18, "word_accuracy_percent": None, "wer": None,
        "content_coverage_percent": None, "score_components": {},
        "screening_indicator": {"severity_hint": 2, "label": "Mild concern", "risk": "low-moderate", "note": ""},
        "phoneme_findings": [], "low_confidence_regions": [], "word_segments": words, "pauses": [],
        "acoustic_features": feats, "segments": [], "preprocessing": {}, "waveform_peaks": [],
        "model": {"asr": "stub", "device": "cpu", "token_count": 11, "verbatim_prompt": True, "rejected_segments": []},
        "model_features": {"acoustic_biomarker_windows": []},
        "processing_time_ms": 1,
    }


def screened_patient(client, monkeypatch):
    monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
    acc = register(client, age=11)
    pid = acc["user"]["patients"][0]["id"]
    session_id = str(uuid.uuid4())
    for task_id, ttype in (("b3-pic-1", "picture"), ("b3-scn-1", "scenario"), ("b3-q-1", "questions")):
        r = client.post("/api/v1/analyze", headers=acc["headers"], files={"audio": ("rec.wav", b"\x00" * 2048, "audio/wav")},
                        data={"session_id": session_id, "patient_id": pid, "age_bracket": "3", "task_type": ttype, "task_id": task_id})
        assert r.status_code == 200, r.text
        assert r.json()["schema_version"] == settings.schema_version == "1.2.0"
        assert "model_features" in r.json()
    r = client.post(f"/api/v1/sessions/{session_id}/finalize", headers=acc["headers"], json={"patient_id": pid})
    assert r.status_code == 200, r.text
    return acc, pid, session_id


def test_plan_before_screening_is_empty(client):
    acc = register(client, age=12)
    pid = acc["user"]["patients"][0]["id"]
    assert client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json() == {"has_profile": False}
    assert client.get(f"/api/v1/therapy/{pid}/assistant", headers=acc["headers"]).status_code == 404


def test_finalize_runs_c2_c3_c4_and_admin_sees_every_stage(client, monkeypatch):
    acc, pid, session_id = screened_patient(client, monkeypatch)
    h = admin_headers(client)

    overview = client.get("/api/v1/admin/pipeline", headers=h).json()
    row = next(r for r in overview["runs"] if r["session_id"] == session_id)
    assert row["status"] == "completed", row
    assert row["articulation_score"] is not None and 1 <= row["severity_level"] <= 4
    assert overview["kpis"]["sessions"] >= 1

    detail = client.get(f"/api/v1/admin/pipeline/{session_id}", headers=h).json()
    assert detail["c2"]["session_articulation"]["scored_recordings"] == 3
    assert detail["c3"]["primary_disorder"] in ("normal", "stuttering", "dysarthria", "articulation")
    assert detail["c4_profile"]["focus"] in ("fluency", "motor_speech", "speech_sounds", "maintenance")
    assert set(detail["stage_timings"]) == {"component2_ms", "component3_ms", "component4_ms"}

    assert client.post(f"/api/v1/admin/pipeline/{session_id}/rerun", headers=h).json()["status"] == "completed"
    models = client.get("/api/v1/admin/models", headers=h).json()
    assert models["component3"]["health"]["status"] == "ok"
    assert models["component4"]["intent_classifier"]["accuracy"] > 50

    therapy = client.get(f"/api/v1/admin/patients/{pid}/therapy", headers=h).json()
    assert therapy["plan"]["engine"]["arms"] and therapy["profile_history"]

    # admin-only
    for path in ("/api/v1/admin/pipeline", f"/api/v1/admin/pipeline/{session_id}", "/api/v1/admin/models",
                 f"/api/v1/admin/patients/{pid}/therapy"):
        assert client.get(path, headers=acc["headers"]).status_code == 403


def test_patient_plan_is_safe_and_adapts(client, monkeypatch):
    acc, pid, _ = screened_patient(client, monkeypatch)
    plan = client.get(f"/api/v1/therapy/{pid}/plan", headers=acc["headers"]).json()
    assert plan["has_profile"] and plan["today"] and len(plan["week"]) == 7
    text = json.dumps(plan).lower()
    for hidden in ("engine", "severity", "dysarthria", "stuttering", "disorder"):
        assert hidden not in text, hidden

    first = plan["today"][0]
    r = client.post(f"/api/v1/therapy/{pid}/attempts", headers=acc["headers"],
                    json={"exercise_id": first["id"], "duration_seconds": 60, "speaking_ratio": 0.8, "syllables": 100,
                          "items_total": 8, "items_clear": 8, "self_rating": "easy"})
    assert r.status_code == 200, r.text
    assert 0 <= r.json()["score"] <= 100 and r.json()["plan"]["progress"]["total_sessions"] == 1

    chat = client.post(f"/api/v1/therapy/{pid}/assistant/chat", headers=acc["headers"], json={"message": "how am I doing?"})
    assert chat.status_code == 200 and chat.json()["source"] in ("classifier", "llm", "fallback")
    assert client.get(f"/api/v1/therapy/{pid}/assistant", headers=acc["headers"]).json()["greeting"]

    other = register(client, age=11)
    assert client.get(f"/api/v1/therapy/{pid}/plan", headers=other["headers"]).status_code == 404
    assert client.post(f"/api/v1/therapy/{pid}/attempts", headers=acc["headers"],
                       json={"exercise_id": "nope"}).status_code == 404


def test_pipeline_failure_never_breaks_finalize(client, monkeypatch):
    import integration.pipeline as pipe

    monkeypatch.setattr(pipe, "_recordings", lambda db, summary: (_ for _ in ()).throw(RuntimeError("boom")))
    acc, pid, session_id = screened_patient(client, monkeypatch)
    row = next(r for r in client.get("/api/v1/admin/pipeline", headers=admin_headers(client)).json()["runs"]
               if r["session_id"] == session_id)
    assert row["status"] == "failed" and "boom" in row["error"]
