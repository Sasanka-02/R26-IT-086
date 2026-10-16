"""
stuttering.py
=============

Multi-label stuttering-event interface:  repetition / prolongation / block.

Each label is scored independently (values are NOT required to sum to 1).
Output shape:

    {"repetition": 0.72, "prolongation": 0.21, "block": 0.61}

The trained model is `MultiOutputClassifier(RandomForestClassifier)`. When it
is missing, a transparent fallback derives partial signals from the REAL
Component 2 disfluency counts (repetition, block) and clearly flags itself;
prolongations come from Component 2's word-duration count.

The interface is deliberately model-agnostic so a HuBERT / wav2vec2 acoustic
model can replace the baseline without touching the pipeline.
"""

from __future__ import annotations

import numpy as np

from .common import STUTTER_EVENTS
from ._models import get_stuttering_bundle


def analyze_stuttering_events(features: dict, vector: list[float]) -> dict:
    bundle = get_stuttering_bundle()
    if bundle is not None:
        return _model_events(bundle, vector)
    return _fallback_events(features)


def _model_events(bundle: dict, vector: list[float]) -> dict:
    model = bundle["model"]
    labels = bundle["labels"]
    X = np.asarray(vector, dtype=float).reshape(1, -1)

    scores: dict[str, float] = {}
    for i, est in enumerate(model.estimators_):
        p = est.predict_proba(X)[0]
        classes = list(getattr(est, "classes_", [0, 1]))
        try:
            rf = est.named_steps["rf"]
            classes = list(rf.classes_)
        except Exception:
            pass
        pos = float(p[classes.index(1)]) if 1 in classes else 0.0
        scores[labels[i]] = round(pos, 4)

    multi_label_positive = [e for e in STUTTER_EVENTS if scores.get(e, 0.0) >= 0.5]

    return {
        "events": {e: scores.get(e) for e in STUTTER_EVENTS},
        "positive_events": multi_label_positive,
        "is_multi_label": True,
        "model_status": "TRAINED",
        "data_source": bundle.get("data_source", "SYNTHETIC_DEMO"),
    }


def _fallback_events(f: dict) -> dict:
    """Partial signal from the real C2 event rates; clearly flagged, no fabricated proba."""
    def sig(x: float) -> float:
        return round(float(1.0 / (1.0 + np.exp(-x))), 4)

    events = {
        "repetition": sig(40 * f["repetition_rate"] - 1.5),
        "prolongation": sig(60 * f["prolongation_rate"] - 1.5),
        "block": sig(0.8 * f["long_pauses_per_min"] - 0.02 * (f["speech_rate_wpm"] - 120) - 1.5),
    }
    return {
        "events": events,
        "positive_events": [e for e in STUTTER_EVENTS if events[e] >= 0.5],
        "is_multi_label": True,
        "model_status": "NOT_TRAINED_PARTIAL_FALLBACK",
        "data_source": "Component 2 fluency-event rates (rule-based)",
    }
