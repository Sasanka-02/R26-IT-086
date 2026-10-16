"""Shared helpers for Component 3 training scripts."""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR  # noqa: F401,E402  (bootstraps sys.path)

import datetime as _dt  # noqa: E402
import json

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from component3.common import FEATURE_ORDER

RANDOM_STATE = 42


def load_demo() -> pd.DataFrame:
    from _paths import DEMO_DATASET_CSV

    if not DEMO_DATASET_CSV.exists():
        raise FileNotFoundError(
            f"Demo dataset not found: {DEMO_DATASET_CSV}\n"
            "Run:  python Training/component3/make_demo_dataset.py"
        )
    df = pd.read_csv(DEMO_DATASET_CSV)
    missing = [c for c in FEATURE_ORDER if c not in df.columns]
    if missing:
        raise ValueError(f"Demo dataset is missing feature columns: {missing}")
    return df


def make_rf_pipeline(n_estimators: int = 300) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def expected_calibration_error(y_true, proba, classes, n_bins: int = 10) -> float:
    """Multi-class ECE using top-1 confidence."""
    proba = np.asarray(proba)
    conf = proba.max(axis=1)
    pred_idx = proba.argmax(axis=1)
    class_list = list(classes)
    y_idx = np.array([class_list.index(y) for y in y_true])
    correct = (pred_idx == y_idx).astype(float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(conf)
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (conf > lo) & (conf <= hi)
        if not mask.any():
            continue
        ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def save_bundle(path, bundle: dict):
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = dict(bundle)
    bundle.setdefault("feature_order", FEATURE_ORDER)
    bundle.setdefault("random_state", RANDOM_STATE)
    bundle.setdefault(
        "trained_at", _dt.datetime.now().replace(microsecond=0).isoformat()
    )
    joblib.dump(bundle, path)
    print(f"  saved -> {path}")


def dump_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
