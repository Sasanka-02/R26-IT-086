"""
severity.py
===========

Severity estimator:  Level 1 (Normal) .. Level 4 (Severe).

Returns the trained model's `predict` + `predict_proba`. Falls back to a
transparent, clearly-flagged heuristic when the model artifact is missing.
"""

from __future__ import annotations

import numpy as np

from .common import SEVERITY_LEVELS, severity_label
from ._models import get_severity_bundle
from .classifier import top_importances


def estimate_severity(features: dict, vector: list[float]) -> dict:
    bundle = get_severity_bundle()
    if bundle is not None:
        return _model_severity(bundle, vector)
    return _heuristic_severity(features)


def _model_severity(bundle: dict, vector: list[float]) -> dict:
    pipe = bundle["pipeline"]
    classes = [int(c) for c in bundle["classes"]]
    X = np.asarray(vector, dtype=float).reshape(1, -1)

    proba = pipe.predict_proba(X)[0]
    prob_map = {lvl: float(p) for lvl, p in zip(classes, proba)}
    probabilities = {str(l): round(prob_map.get(l, 0.0), 4) for l in SEVERITY_LEVELS}

    level = int(pipe.predict(X)[0])
    # ordinal-expected level (probability-weighted) kept for transparency
    expected = float(sum(l * prob_map.get(l, 0.0) for l in SEVERITY_LEVELS))

    return {
        "severity_level": level,
        "severity_label": severity_label(level),
        "probabilities": probabilities,
        "expected_level": round(expected, 3),
        "model_status": "TRAINED",
        "data_source": bundle.get("data_source", "SYNTHETIC_DEMO"),
        "feature_importance": top_importances(pipe),
    }


def _heuristic_severity(f: dict) -> dict:
    """Documented fallback: maps a 0..1 impairment score to Level 1-4."""
    impairment = np.clip(
        0.30 * (1 - f["articulation_score"] / 100.0)
        + 0.25 * (1 - f["fluency_score"] / 100.0)
        + 0.20 * f["dysarthria_probability"]
        + 0.15 * min(1.0, 5 * (f["repetition_rate"] + f["prolongation_rate"]))
        + 0.10 * min(1.0, f["flagged_sound_count"] / 5.0),
        0.0,
        1.0,
    )
    if impairment < 0.15:
        level = 1
    elif impairment < 0.40:
        level = 2
    elif impairment < 0.65:
        level = 3
    else:
        level = 4

    # crude spread around the chosen level
    probs = {1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1}
    probs[level] = 0.7
    total = sum(probs.values())
    probabilities = {str(l): round(probs[l] / total, 4) for l in SEVERITY_LEVELS}

    return {
        "severity_level": level,
        "severity_label": severity_label(level),
        "probabilities": probabilities,
        "expected_level": float(level),
        "model_status": "NOT_TRAINED_HEURISTIC_FALLBACK",
        "data_source": "none (rule-based)",
        "feature_importance": [],
    }
