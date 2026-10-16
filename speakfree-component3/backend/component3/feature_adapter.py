"""
feature_adapter.py
==================

Converts raw Component 2 output into the fixed-order Component 3 feature
vector defined in `common.FEATURE_ORDER`.

Design rules (per Component 3 spec):
    - validate input
    - handle missing fields safely (impute with documented defaults)
    - normalise numeric fields where appropriate
    - preserve session_id / user_id (handled by the pipeline, not here)
    - preserve Component 2 confidence values
    - reject invalid input with clear errors

This module NEVER mutates the incoming Component 2 payload and never re-runs
Component 1 / Component 2 processing.
"""

from __future__ import annotations

from typing import Any

from .common import (
    FEATURE_ORDER,
    FEATURE_DEFAULTS,
    RISK_LEVEL_ORDINAL,
)


class FeatureAdapterError(ValueError):
    """Raised when Component 2 output cannot be adapted."""


# ---------------------------------------------------------------------------
# Payload normalisation
# ---------------------------------------------------------------------------

def _resolve_component2(payload: Any) -> dict:
    """
    Accepts any of the shapes Component 2 / the C2 API can produce and returns
    the inner `component2_output`-style dict.

    Supported inputs:
        1. Full C2 API response: {"component2_output": {...}, "component3_input": {...}}
        2. The component2_output object itself: {"ml_prediction": {...}, ...}
        3. Just the handoff dict: {"dysarthria_risk_score": ..., "fluency_score": ...}
    """
    if not isinstance(payload, dict):
        raise FeatureAdapterError(
            "component2_output must be a JSON object, "
            f"got {type(payload).__name__}."
        )

    if not payload:
        raise FeatureAdapterError("component2_output is empty.")

    # Shape 1 - full API response
    if "component2_output" in payload and isinstance(
        payload["component2_output"], dict
    ):
        return payload["component2_output"]

    # Shape 2 / 3 - already the output object or the handoff dict
    return payload


def _get_handoff(c2: dict) -> dict:
    """Return the Component-3-ready handoff dict if present, else {}."""
    handoff = c2.get("component3_ready_output")
    if isinstance(handoff, dict):
        return handoff
    # Shape 3: the payload *is* the handoff dict
    if "dysarthria_risk_score" in c2 or "fluency_score" in c2:
        return c2
    return {}


def _num(value: Any, default: float) -> float:
    """Coerce to float; fall back to default for None / non-numeric / NaN."""
    if value is None:
        return float(default)
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float(default)
    if f != f:  # NaN
        return float(default)
    return f


def _first(*values):
    """First value that is not None."""
    for v in values:
        if v is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def adapt_features(component2_output: Any) -> dict:
    """
    Returns:
        {
            "features": {name: float, ...},          # keyed by FEATURE_ORDER
            "vector": [float, ...],                   # ordered per FEATURE_ORDER
            "missing_fields": [str, ...],             # C2 fields that were absent
            "component2_confidence": {                # preserved, not consumed
                "dysarthria_probability": float|None,
                "alignment_reliability": float|None,
                "alignment_uncertain": bool|None,
                "asr_confidence_score": float|None,
            },
            "source_shape": "api_response|output_object|handoff_only",
        }
    """
    c2 = _resolve_component2(component2_output)
    handoff = _get_handoff(c2)

    ml = c2.get("ml_prediction") if isinstance(c2.get("ml_prediction"), dict) else {}
    stutter = (
        c2.get("stuttering_analysis")
        if isinstance(c2.get("stuttering_analysis"), dict)
        else {}
    )
    fluency = stutter.get("fluency") if isinstance(stutter.get("fluency"), dict) else {}
    timing = (
        stutter.get("timing") if isinstance(stutter.get("timing"), dict) else {}
    )
    speech_rate = (
        stutter.get("speech_rate")
        if isinstance(stutter.get("speech_rate"), dict)
        else {}
    )
    articulation = (
        c2.get("articulation_analysis")
        if isinstance(c2.get("articulation_analysis"), dict)
        else {}
    )
    subscores = (
        articulation.get("subscores")
        if isinstance(articulation.get("subscores"), dict)
        else {}
    )
    timing_analysis = (
        c2.get("timing_analysis")
        if isinstance(c2.get("timing_analysis"), dict)
        else {}
    )
    asr = c2.get("asr_analysis") if isinstance(c2.get("asr_analysis"), dict) else {}

    if not handoff and not ml and not stutter:
        raise FeatureAdapterError(
            "Unrecognised Component 2 output: expected at least one of "
            "'component3_ready_output', 'ml_prediction' or "
            "'stuttering_analysis'."
        )

    # -- raw values, tolerating any of the known C2 shapes --------------------
    raw = {}

    raw["dysarthria_probability"] = _first(
        handoff.get("dysarthria_probability"),
        ml.get("dysarthria_probability"),
    )
    raw["dysarthria_risk_score"] = _first(
        handoff.get("dysarthria_risk_score"),
        ml.get("dysarthria_risk_score"),
    )
    raw["risk_level_ordinal"] = RISK_LEVEL_ORDINAL.get(
        str(_first(handoff.get("risk_level"), ml.get("risk_level"), "")).lower(),
        None,
    )

    raw["fluency_score"] = _first(
        handoff.get("fluency_score"), fluency.get("fluency_score")
    )
    raw["word_repetition_count"] = _first(
        handoff.get("word_repetition_count"),
        len(stutter["word_repetitions"])
        if isinstance(stutter.get("word_repetitions"), list)
        else None,
    )
    raw["phrase_repetition_count"] = _first(
        handoff.get("phrase_repetition_count"),
        len(stutter["phrase_repetitions"])
        if isinstance(stutter.get("phrase_repetitions"), list)
        else None,
    )
    raw["filler_count"] = _first(
        handoff.get("filler_count"),
        len(stutter["fillers_and_hesitations"])
        if isinstance(stutter.get("fillers_and_hesitations"), list)
        else None,
    )
    raw["speech_rate_wpm"] = _first(
        handoff.get("speech_rate_wpm"),
        speech_rate.get("words_per_minute"),
        fluency.get("words_per_minute"),
    )
    raw["long_pause_count"] = _first(
        handoff.get("long_pause_count"), timing.get("long_pause_count")
    )
    raw["total_disfluency_indicators"] = stutter.get(
        "total_observable_disfluency_indicators"
    )
    raw["repetition_rate"] = fluency.get("repetition_rate")
    raw["filler_rate"] = fluency.get("filler_rate")

    raw["timing_consistency"] = _first(
        handoff.get("timing_consistency"),
        timing_analysis.get("timing_consistency_score"),
        subscores.get("timing_consistency"),
    )
    raw["duration_variation"] = _first(
        handoff.get("duration_variation"),
        timing_analysis.get("duration_variation"),
    )
    raw["phoneme_count"] = _first(
        handoff.get("phoneme_count"),
        timing_analysis.get("phoneme_count"),
    )
    raw["alignment_reliability"] = _first(
        handoff.get("alignment_reliability"),
        (c2.get("alignment") or {}).get("reliability")
        if isinstance(c2.get("alignment"), dict)
        else None,
    )

    _align_uncertain = _first(
        handoff.get("alignment_uncertain"),
        (c2.get("alignment") or {}).get("uncertainty_flag")
        if isinstance(c2.get("alignment"), dict)
        else None,
    )
    raw["alignment_uncertain"] = (
        None if _align_uncertain is None else (1.0 if _align_uncertain else 0.0)
    )

    raw["overall_articulation_indicator"] = subscores.get(
        "overall_articulation_indicator"
    )
    raw["phoneme_consistency"] = subscores.get("phoneme_consistency")
    raw["acoustic_model_component"] = subscores.get("acoustic_model_component")

    # -- build the fixed-order vector with documented imputation -------------
    features: dict[str, float] = {}
    missing: list[str] = []

    for name in FEATURE_ORDER:
        value = raw.get(name)
        if value is None:
            missing.append(name)
            features[name] = float(FEATURE_DEFAULTS[name])
        else:
            features[name] = _num(value, FEATURE_DEFAULTS[name])

    # light, bounded normalisation of the obviously-bounded fields
    features["dysarthria_probability"] = _clip(features["dysarthria_probability"], 0.0, 1.0)
    for pct in (
        "dysarthria_risk_score",
        "fluency_score",
        "timing_consistency",
        "alignment_reliability",
        "overall_articulation_indicator",
        "phoneme_consistency",
        "acoustic_model_component",
    ):
        features[pct] = _clip(features[pct], 0.0, 100.0)

    vector = [features[name] for name in FEATURE_ORDER]

    return {
        "features": features,
        "vector": vector,
        "missing_fields": missing,
        "component2_confidence": {
            "dysarthria_probability": _opt(raw["dysarthria_probability"]),
            "alignment_reliability": _opt(raw["alignment_reliability"]),
            "alignment_uncertain": (
                None
                if raw["alignment_uncertain"] is None
                else bool(raw["alignment_uncertain"])
            ),
            "asr_confidence_score": _opt(asr.get("asr_confidence_score")),
        },
        "source_shape": _source_shape(component2_output, handoff),
    }


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _opt(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _source_shape(payload, handoff) -> str:
    if isinstance(payload, dict) and "component2_output" in payload:
        return "api_response"
    if handoff and isinstance(payload, dict) and "component3_ready_output" not in payload:
        return "handoff_only"
    return "output_object"
