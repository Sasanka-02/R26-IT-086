"""
classifier.py
=============

Multi-disorder classification interface:  normal / stuttering / dysarthria /
articulation.

Returns real `predict_proba()` output from the trained RandomForest. If the
model artifact is missing it falls back to a TRANSPARENT, clearly-labelled
heuristic (never a hard-coded / faked ML result) so the pipeline still
responds during development.
"""

from __future__ import annotations

import numpy as np

from .common import DISORDER_CLASSES, FEATURE_LABELS, FEATURE_ORDER
from ._models import get_disorder_bundle


def classify_disorder(features: dict, vector: list[float]) -> dict:
    bundle = get_disorder_bundle()
    if bundle is not None:
        return _model_classify(bundle, vector)
    return _heuristic_classify(features)


# ---------------------------------------------------------------------------
# Trained model path
# ---------------------------------------------------------------------------

def _model_classify(bundle: dict, vector: list[float]) -> dict:
    pipe = bundle["pipeline"]
    classes = [str(c) for c in bundle["classes"]]
    X = np.asarray(vector, dtype=float).reshape(1, -1)

    proba = pipe.predict_proba(X)[0]
    prob_map = {cls: float(p) for cls, p in zip(classes, proba)}
    probabilities = {c: round(prob_map.get(c, 0.0), 4) for c in DISORDER_CLASSES}

    predicted = max(probabilities, key=probabilities.get)

    return {
        "predicted_disorder": predicted,
        "probabilities": probabilities,
        "model_status": "TRAINED",
        "data_source": bundle.get("data_source", "SYNTHETIC_DEMO"),
        "estimator_proba_std": _tree_std(pipe, X, classes),
        "feature_importance": top_importances(pipe),
    }


def top_importances(pipe, k: int = 6) -> list[dict]:
    """Global RandomForest feature importances (mean impurity decrease), largest first."""
    try:
        rf = pipe.named_steps["classifier"]
        pairs = sorted(zip(FEATURE_ORDER, rf.feature_importances_), key=lambda t: t[1], reverse=True)[:k]
        return [{"feature": n, "label": FEATURE_LABELS[n], "importance": round(float(v), 4)} for n, v in pairs]
    except Exception:
        return []


def _tree_std(pipe, X, classes) -> dict:
    """Per-class std of predict_proba across the RF's trees (epistemic spread)."""
    try:
        rf = pipe.named_steps["classifier"]
        Xt = pipe.named_steps["imputer"].transform(X)
        per_tree = np.stack([est.predict_proba(Xt)[0] for est in rf.estimators_])
        std = per_tree.std(axis=0)
        rf_classes = [str(c) for c in rf.classes_]
        out = {c: 0.0 for c in DISORDER_CLASSES}
        for c, s in zip(rf_classes, std):
            if c in out:
                out[c] = round(float(s), 4)
        return out
    except Exception:
        return {c: 0.0 for c in DISORDER_CLASSES}


# ---------------------------------------------------------------------------
# Transparent fallback (NOT a trained model - clearly flagged)
# ---------------------------------------------------------------------------

def _heuristic_classify(f: dict) -> dict:
    """
    Documented linear-score heuristic over Component 1/2 indicators. Used ONLY when the
    trained model file is absent. `model_status` makes this explicit in the report.
    """
    dys = f["dysarthria_probability"]
    disfluency = 6 * f["repetition_rate"] + 6 * f["prolongation_rate"] + 0.4 * f["long_pauses_per_min"] + 3 * f["filler_rate"]
    scores = {
        "normal": 1.4 * f["fluency_score"] / 100 + 1.2 * f["articulation_score"] / 100 + (1 - dys) - disfluency,
        "stuttering": 1.6 * disfluency + 1.2 * (1 - f["fluency_score"] / 100),
        "dysarthria": 2.2 * dys + 1.0 * (1 - f["articulation_score"] / 100) + 0.15 * max(0.0, 4.0 - f["articulation_rate_sps"]),
        "articulation": 0.35 * f["flagged_sound_count"] + 1.2 * (1 - f["pronunciation_score"] / 100),
    }
    arr = np.array([scores[c] for c in DISORDER_CLASSES], dtype=float)
    arr = arr - arr.max()
    soft = np.exp(arr) / np.exp(arr).sum()
    probabilities = {c: round(float(p), 4) for c, p in zip(DISORDER_CLASSES, soft)}
    return {
        "predicted_disorder": max(probabilities, key=probabilities.get),
        "probabilities": probabilities,
        "model_status": "NOT_TRAINED_HEURISTIC_FALLBACK",
        "data_source": "none (rule-based)",
        "estimator_proba_std": {c: 0.0 for c in DISORDER_CLASSES},
        "feature_importance": [],
    }
