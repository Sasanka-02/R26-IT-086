"""Component 3 tests: feature adapter, acoustic windows, model cascade, fallbacks, report contract."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component3 import _models, run_component3  # noqa: E402
from component3.acoustic_windows import extract_acoustic_windows, window_starts  # noqa: E402
from component3.common import DISORDER_CLASSES, FEATURE_ORDER  # noqa: E402
from component3.feature_adapter import FeatureAdapterError, adapt_features  # noqa: E402


def handoff(**over):
    base = {
        "schema_version": "4.0",
        "session_id": "s1",
        "patient_id": "SF-1",
        "articulation_score": 88.0,
        "pooled_confidence_C": 0.88,
        "pooled_clear_word_ratio": 0.95,
        "articulation_reliability": "normal",
        "fluency_events": {"filler_rate": 0.01, "repetition_rate": 0.0, "prolongation_rate": 0.0,
                           "long_pauses_per_min": 0.3},
        "component1": {"overall_confidence_percent": 89, "dysfluency_ratio": 0.04, "fluency_score": 90,
                       "pronunciation_score": 89, "words_per_minute": 130, "articulation_rate_syll_per_sec": 4.4,
                       "pause_rate_per_min": 8, "longest_pause_sec": 0.8, "snr_db": 30},
        "flagged_sounds": [],
        "acoustic_biomarker_windows": [],
    }
    base.update(over)
    return base


def test_adapter_builds_ordered_vector_and_reports_imputation():
    out = adapt_features(handoff())
    assert len(out["vector"]) == len(FEATURE_ORDER)
    assert out["features"]["articulation_score"] == 88.0
    # no acoustic windows -> stage 1 cannot run -> P(dysarthria) imputed
    assert out["missing_fields"] == ["dysarthria_probability"]
    assert out["stage1_acoustic"]["status"] in ("NO_ACOUSTIC_WINDOWS", "MODEL_MISSING")


def test_adapter_accepts_full_component2_report():
    out = adapt_features({"component3_input": handoff(articulation_score=40)})
    assert out["features"]["articulation_score"] == 40


def test_adapter_rejects_bad_input():
    with pytest.raises(FeatureAdapterError):
        adapt_features({"foo": 1})
    with pytest.raises(FeatureAdapterError):
        adapt_features({"component3_input": None})


def test_window_starts_are_non_overlapping_and_capped():
    starts = window_starts([(0.5, 1.5), (1.6, 2.0), (5.0, 6.0), (9.0, 10.0), (13.0, 14.0)], 20.0)
    assert len(starts) <= 3
    assert all(b - a >= 3.0 - 1e-9 for a, b in zip(starts, starts[1:]))


def test_acoustic_windows_match_torgo_feature_columns():
    sr = 16000
    t = np.arange(int(sr * 4)) / sr
    voice = 0.2 * np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 3 * t) > 0)
    windows = extract_acoustic_windows(voice.astype(np.float32), sr, [(0.5, 3.5)])
    assert len(windows) == 1
    bundle = _models.get_dysarthria_real_bundle()
    if bundle is not None:
        assert set(bundle["feature_columns"]) <= set(windows[0]["features"])
        out = adapt_features(handoff(acoustic_biomarker_windows=windows))
        assert out["stage1_acoustic"]["status"] == "TRAINED"
        assert 0.0 <= out["features"]["dysarthria_probability"] <= 1.0


def test_full_cascade_report_contract():
    report = run_component3("s1", "SF-1", handoff())
    assert report["primary_disorder"] in DISORDER_CLASSES
    assert 1 <= report["severity_level"] <= 4
    assert report["risk_level"] in ("Low", "Medium", "High")
    assert abs(sum(report["disorder_breakdown"].values()) - 1.0) < 0.01
    assert set(report["stuttering_events"]) == {"repetition", "prolongation", "block"}
    assert report["therapy_focus"] in ("maintenance", "fluency", "motor_speech", "speech_sounds")
    assert len(report["feature_vector"]) == len(FEATURE_ORDER)
    assert report["unified_score"]["scoring_explanation"]


def test_trained_models_separate_obvious_profiles():
    if _models.get_disorder_bundle() is None:
        pytest.skip("models not trained")
    stutter = handoff(fluency_events={"filler_rate": 0.08, "repetition_rate": 0.15, "prolongation_rate": 0.07,
                                      "long_pauses_per_min": 5.0})
    stutter["component1"] = {**stutter["component1"], "fluency_score": 45, "dysfluency_ratio": 0.2, "longest_pause_sec": 3.0}
    assert run_component3("s", "u", stutter)["primary_disorder"] == "stuttering"
    assert run_component3("s", "u", handoff())["primary_disorder"] == "normal"


def test_heuristic_fallback_is_flagged(monkeypatch):
    for name in ("get_disorder_bundle", "get_severity_bundle", "get_stuttering_bundle"):
        monkeypatch.setattr(f"component3.classifier.{name}" if name == "get_disorder_bundle"
                            else f"component3.severity.{name}" if name == "get_severity_bundle"
                            else f"component3.stuttering.{name}", lambda: None)
    report = run_component3("s1", "SF-1", handoff())
    assert report["model_status"]["any_untrained_fallback_used"] is True
    assert report["model_status"]["disorder_classifier"] == "NOT_TRAINED_HEURISTIC_FALLBACK"
