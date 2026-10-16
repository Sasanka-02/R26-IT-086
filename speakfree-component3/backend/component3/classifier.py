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

from .common import DISORDER_CLASSES
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
    }


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
    Documented linear-score heuristic over Component 2 indicators. Used ONLY
    when the trained model file is absent. `model_status` makes this explicit
    and the pipeline surfaces it in the report.
    """
    dys = f["dysarthria_probability"]
    scores = {
        "normal": 0.0,
        "stuttering": 0.0,
        "dysarthria": 0.0,
        "articulation": 0.0,
    }

    scores["dysarthria"] += 2.2 * dys
    scores["dysarthria"] += 0.9 * (1 - f["timing_consistency"] / 100.0)
    scores["dysarthria"] += 0.8 * min(1.0, f["duration_variation"])

    disfluency = (
        f["word_repetition_count"]
        + f["phrase_repetition_count"]
        + 0.5 * f["filler_count"]
        + f["long_pause_count"]
    )
    scores["stuttering"] += 0.35 * disfluency
    scores["stuttering"] += 1.2 * (1 - f["fluency_score"] / 100.0)

    scores["articulation"] += 1.6 * (1 - f["phoneme_consistency"] / 100.0)
    scores["articulation"] += 0.7 * (1 - f["overall_articulation_indicator"] / 100.0)
    scores["articulation"] += 0.5 * dys

    scores["normal"] += 1.4 * (f["fluency_score"] / 100.0)
    scores["normal"] += 1.0 * (1 - dys)
    scores["normal"] += 0.6 * (f["timing_consistency"] / 100.0)
    scores["normal"] -= 0.3 * disfluency

    arr = np.array([scores[c] for c in DISORDER_CLASSES], dtype=float)
    arr = arr - arr.max()
    soft = np.exp(arr) / np.exp(arr).sum()
    probabilities = {c: round(float(p), 4) for c, p in zip(DISORDER_CLASSES, soft)}
    predicted = max(probabilities, key=probabilities.get)

    return {
        "predicted_disorder": predicted,
        "probabilities": probabilities,
        "model_status": "NOT_TRAINED_HEURISTIC_FALLBACK",
        "data_source": "none (rule-based)",
        "estimator_proba_std": {c: 0.0 for c in DISORDER_CLASSES},
    }
