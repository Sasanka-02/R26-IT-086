"""
Component 3 smoke / contract tests.

Run from the backend directory:
    python -m pytest tests/component3 -q
or without pytest:
    python tests/component3/test_pipeline.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from component3.common import DISORDER_CLASSES, SEVERITY_LEVELS
from component3.feature_adapter import adapt_features, FeatureAdapterError
from component3.pipeline import run_component3, health


# --- realistic Component 2 payloads (shapes actually produced by C2) --------

C2_HANDOFF_ONLY = {
    "dysarthria_risk_score": 71.2,
    "dysarthria_probability": 0.712,
    "risk_level": "high",
    "fluency_score": 55.0,
    "word_repetition_count": 5,
    "phrase_repetition_count": 2,
    "filler_count": 4,
    "speech_rate_wpm": 92.0,
    "long_pause_count": 4,
    "timing_consistency": None,
    "duration_variation": None,
    "phoneme_count": 0,
    "alignment_reliability": None,
    "alignment_uncertain": True,
}

C2_FULL_OUTPUT = {
    "component2_output": {
        "ml_prediction": {
            "predicted_class": "healthy",
            "healthy_probability": 0.82,
            "dysarthria_probability": 0.18,
            "dysarthria_risk_score": 18.0,
            "risk_level": "low",
        },
        "stuttering_analysis": {
            "word_repetitions": [],
            "phrase_repetitions": [],
            "fillers_and_hesitations": [{"word": "um"}],
            "timing": {"long_pause_count": 0, "pause_count": 2},
            "speech_rate": {"words_per_minute": 148.0},
            "fluency": {
                "fluency_score": 94.0,
                "repetition_rate": 0.0,
                "filler_rate": 0.02,
            },
            "total_observable_disfluency_indicators": 1,
        },
        "articulation_analysis": {
            "subscores": {
                "overall_articulation_indicator": 88.0,
                "phoneme_consistency": 90.0,
                "timing_consistency": 86.0,
                "acoustic_model_component": 82.0,
            }
        },
        "timing_analysis": {
            "timing_consistency_score": 86.0,
            "duration_variation": 0.31,
            "phoneme_count": 24,
        },
        "component3_ready_output": {
            "dysarthria_risk_score": 18.0,
            "dysarthria_probability": 0.18,
            "risk_level": "low",
            "fluency_score": 94.0,
            "word_repetition_count": 0,
            "phrase_repetition_count": 0,
            "filler_count": 1,
            "speech_rate_wpm": 148.0,
            "long_pause_count": 0,
            "timing_consistency": 86.0,
            "duration_variation": 0.31,
            "phoneme_count": 24,
            "alignment_reliability": 79.0,
            "alignment_uncertain": False,
        },
        "clinical_note": "research prototype",
    }
}


def test_adapter_handoff_only():
    r = adapt_features(C2_HANDOFF_ONLY)
    assert len(r["vector"]) == len(r["features"])
    assert r["features"]["dysarthria_probability"] == 0.712
    assert "timing_consistency" in r["missing_fields"]
    assert r["source_shape"] == "handoff_only"


def test_adapter_full_output():
    r = adapt_features(C2_FULL_OUTPUT)
    assert r["source_shape"] == "api_response"
    assert r["features"]["phoneme_count"] == 24
    assert r["features"]["alignment_uncertain"] == 0.0
    assert r["missing_fields"] == []


def test_adapter_rejects_garbage():
    for bad in [None, {}, {"foo": "bar"}, [1, 2, 3]]:
        try:
            adapt_features(bad)
        except FeatureAdapterError:
            continue
        raise AssertionError(f"expected FeatureAdapterError for {bad!r}")


def _check_report(rep):
    assert rep["primary_disorder"] in DISORDER_CLASSES
    assert rep["severity_level"] in SEVERITY_LEVELS
    assert rep["risk_level"] in {"Low", "Medium", "High"}
    assert 0.0 <= rep["confidence_score"] <= 1.0
    assert set(rep["disorder_breakdown"]) == set(DISORDER_CLASSES)
    assert abs(sum(rep["disorder_breakdown"].values()) - 1.0) < 0.05
    assert set(rep["stuttering_events"]) == {"repetition", "prolongation", "block"}
    assert isinstance(rep["recommendations"], list) and rep["recommendations"]
    assert rep["model_version"]
    assert "disclaimer" in rep


def test_pipeline_handoff_only():
    rep = run_component3("sess-1", "user-1", C2_HANDOFF_ONLY)
    _check_report(rep)
    assert rep["session_id"] == "sess-1"


def test_pipeline_full_output():
    rep = run_component3(None, None, C2_FULL_OUTPUT)
    _check_report(rep)
    assert rep["session_id"].startswith("c3-")
    assert rep["user_id"] == "anonymous"


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert "models" in h


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FAIL  {fn.__name__}: {exc!r}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
