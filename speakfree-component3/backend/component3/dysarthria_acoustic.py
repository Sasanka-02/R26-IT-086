"""
Stage 1 of the Component 3 model cascade - the REAL-DATA acoustic dysarthria model.

    P(dysarthria | session) = (1/K) Σ_k P_RF(dysarthria | x_k)       k = acoustic windows

The RandomForest was trained on the TORGO research corpus (speaker-independent GroupKFold,
see training/train_dysarthria_real_torgo.py). Its output becomes the `dysarthria_probability`
feature of the stage-2 multi-disorder / severity models.
"""
from __future__ import annotations

import numpy as np

from ._models import get_dysarthria_real_bundle


def predict_dysarthria(windows: list[dict] | None) -> dict:
    windows = [w for w in (windows or []) if isinstance(w, dict) and isinstance(w.get("features"), dict)]
    bundle = get_dysarthria_real_bundle()
    if bundle is None:
        return {"status": "MODEL_MISSING", "probability": None, "windows_used": 0, "per_window": []}
    if not windows:
        return {"status": "NO_ACOUSTIC_WINDOWS", "probability": None, "windows_used": 0, "per_window": []}

    cols = bundle["feature_columns"]
    X = np.array([[float(w["features"].get(c, np.nan)) for c in cols] for w in windows], dtype=float)
    proba = bundle["pipeline"].predict_proba(X)[:, 1]
    return {
        "status": "TRAINED",
        "data_source": bundle.get("data_source", "TORGO (research dataset)"),
        "probability": round(float(np.mean(proba)), 4),
        "windows_used": len(windows),
        "per_window": [
            {"analysis_id": w.get("analysis_id"), "task_type": w.get("task_type"),
             "start_sec": w.get("start_sec"), "probability": round(float(p), 4)}
            for w, p in zip(windows, proba)
        ],
        "cv_metrics": bundle.get("cv_metrics"),
    }
