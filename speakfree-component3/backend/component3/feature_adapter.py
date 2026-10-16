"""
feature_adapter.py
==================

Converts the Component 2 hand-off (`component3_input`, schema 4.0) into the fixed-order
Component 3 feature vector defined in `common.FEATURE_ORDER`.

Design rules:
    - validate input, reject unusable payloads with clear errors
    - impute missing fields with documented neutral defaults (and report which)
    - bounded normalisation of percentage / ratio fields
    - never mutate the incoming payload, never re-run Component 1 / Component 2 processing

Stage 1 of the model cascade (the real-data TORGO acoustic model) runs here, because its
output is one of the stage-2 features.
"""

from __future__ import annotations

from typing import Any

from .common import FEATURE_DEFAULTS, FEATURE_ORDER
from .dysarthria_acoustic import predict_dysarthria


class FeatureAdapterError(ValueError):
    """Raised when the Component 2 hand-off cannot be adapted."""


def _resolve(payload: Any) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise FeatureAdapterError("component2_output must be a non-empty JSON object.")
    # full Component 2 report -> take its hand-off block
    if isinstance(payload.get("component3_input"), dict):
        return payload["component3_input"]
    if payload.get("component3_input", "missing") is None:
        raise FeatureAdapterError("Component 2 produced no hand-off (no scorable words in the session).")
    if "articulation_score" not in payload:
        raise FeatureAdapterError("Unrecognised Component 2 output: expected 'articulation_score' or 'component3_input'.")
    return payload


def _num(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def adapt_features(component2_output: Any) -> dict:
    """
    Returns {features, vector, missing_fields, stage1_acoustic, component2_confidence, source_schema}.
    """
    c2 = _resolve(component2_output)
    c1 = c2.get("component1") if isinstance(c2.get("component1"), dict) else {}
    ev = c2.get("fluency_events") if isinstance(c2.get("fluency_events"), dict) else {}
    sounds = c2.get("flagged_sounds") if isinstance(c2.get("flagged_sounds"), list) else None

    stage1 = predict_dysarthria(c2.get("acoustic_biomarker_windows"))

    raw = {
        "articulation_score": c2.get("articulation_score"),
        "clear_word_ratio": c2.get("pooled_clear_word_ratio"),
        "kept_token_confidence": c2.get("pooled_confidence_C"),
        "asr_confidence": c1.get("overall_confidence_percent"),
        "dysfluency_ratio": c1.get("dysfluency_ratio"),
        "fluency_score": c1.get("fluency_score"),
        "pronunciation_score": c1.get("pronunciation_score"),
        "speech_rate_wpm": c1.get("words_per_minute"),
        "articulation_rate_sps": c1.get("articulation_rate_syll_per_sec"),
        "pause_rate_per_min": c1.get("pause_rate_per_min"),
        "longest_pause_sec": c1.get("longest_pause_sec"),
        "filler_rate": ev.get("filler_rate"),
        "repetition_rate": ev.get("repetition_rate"),
        "prolongation_rate": ev.get("prolongation_rate"),
        "long_pauses_per_min": ev.get("long_pauses_per_min"),
        "flagged_sound_count": len(sounds) if sounds is not None else None,
        "dysarthria_probability": stage1["probability"],
    }

    features: dict[str, float] = {}
    missing: list[str] = []
    for name in FEATURE_ORDER:
        value = _num(raw.get(name))
        if value is None:
            missing.append(name)
            value = float(FEATURE_DEFAULTS[name])
        features[name] = value

    for pct in ("articulation_score", "asr_confidence", "fluency_score", "pronunciation_score"):
        features[pct] = _clip(features[pct], 0.0, 100.0)
    for ratio in ("clear_word_ratio", "kept_token_confidence", "dysfluency_ratio", "filler_rate",
                  "repetition_rate", "prolongation_rate", "dysarthria_probability"):
        features[ratio] = _clip(features[ratio], 0.0, 1.0)

    return {
        "features": features,
        "vector": [features[name] for name in FEATURE_ORDER],
        "missing_fields": missing,
        "stage1_acoustic": stage1,
        "component2_confidence": {
            "articulation_reliability": c2.get("articulation_reliability"),
            "asr_confidence_percent": _num(c1.get("overall_confidence_percent")),
            "snr_db": _num(c1.get("snr_db")),
        },
        "source_schema": str(c2.get("schema_version") or "unknown"),
    }
