"""
train_dysarthria_real_torgo.py
==============================

The ONE Component 3 model trained on REAL research data.

Dataset : TORGO  (dataset/torgo/features.csv - already in the repo)
Task    : binary  healthy (0) vs dysarthria (1)
Split   : speaker-independent 5-fold GroupKFold (no speaker in both
          train and test) -> the reported metrics are leakage-safe
Model   : RandomForestClassifier(class_weight="balanced", random_state=42)
Output  : Models/component3/dysarthria_real_torgo.joblib
          Models/component3/dysarthria_real_torgo_metrics.json

This gives Component 3 a genuine, speaker-independent research result for the
"severity / risk prediction for dysarthria" objective. It is INDEPENDENT of
the demo models above. It reuses TORGO exactly as Component 2 did (same CSV,
same target) but is trained and evaluated by Component 3's own script.
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR, TORGO_FEATURES_CSV, TORGO_SELECTED_FEATURES  # noqa

import json  # noqa: E402

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

from component3.common import MODEL_DIR
from _trainutil import RANDOM_STATE, save_bundle

TARGET = "speech_status"
LABEL_MAP = {"healthy": 0, "dysarthria": 1}
METRICS_JSON = MODEL_DIR / "dysarthria_real_torgo_metrics.json"


def _feature_columns(df: pd.DataFrame) -> list[str]:
    if TORGO_SELECTED_FEATURES.exists():
        sel = [
            line.strip()
            for line in TORGO_SELECTED_FEATURES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        sel = [c for c in sel if c in df.columns]
        if sel:
            return sel
    exclude = {TARGET, "filename", "speaker_id", "transcription", "gender", "audio_path"}
    return [
        c for c in df.columns
        if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
    ]


def main():
    print("=" * 60)
    print("COMPONENT 3 - REAL DYSARTHRIA MODEL (TORGO, speaker-independent)")
    print("=" * 60)

    if not TORGO_FEATURES_CSV.exists():
        raise FileNotFoundError(
            f"TORGO feature table not found: {TORGO_FEATURES_CSV}\n"
            "This script requires the Component 2 TORGO dataset to be present."
        )

    df = pd.read_csv(TORGO_FEATURES_CSV)
    df = df[df[TARGET].isin(LABEL_MAP)].copy()
    y = df[TARGET].map(LABEL_MAP).to_numpy()
    groups = df["speaker_id"].to_numpy()
    feat_cols = _feature_columns(df)
    X = df[feat_cols].to_numpy(dtype=float)

    print(f"samples={len(df)}  features={len(feat_cols)}  "
          f"speakers={len(np.unique(groups))}")
    print(f"healthy={int((y == 0).sum())}  dysarthria={int((y == 1).sum())}")

    def new_pipe():
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

    gkf = GroupKFold(n_splits=5)
    fold_rows, oof_true, oof_pred, oof_proba = [], [], [], []

    for k, (tr, te) in enumerate(gkf.split(X, y, groups), start=1):
        pipe = new_pipe()
        pipe.fit(X[tr], y[tr])
        p = pipe.predict(X[te])
        pr = pipe.predict_proba(X[te])[:, 1]
        oof_true.extend(y[te]); oof_pred.extend(p); oof_proba.extend(pr)
        fold_rows.append(
            {
                "fold": k,
                "test_speakers": sorted(set(groups[te].tolist())),
                "accuracy": round(accuracy_score(y[te], p), 4),
                "balanced_accuracy": round(balanced_accuracy_score(y[te], p), 4),
                "f1": round(f1_score(y[te], p, zero_division=0), 4),
                "roc_auc": round(roc_auc_score(y[te], pr), 4),
            }
        )
        print(f"  fold {k}: {fold_rows[-1]}")

    oof_true = np.array(oof_true)
    oof_pred = np.array(oof_pred)
    oof_proba = np.array(oof_proba)

    summary = {
        "accuracy": round(float(accuracy_score(oof_true, oof_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(oof_true, oof_pred)), 4),
        "precision": round(float(precision_score(oof_true, oof_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(oof_true, oof_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(oof_true, oof_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(oof_true, oof_proba)), 4),
        "confusion_matrix": confusion_matrix(oof_true, oof_pred).tolist(),
        "confusion_matrix_labels": ["healthy", "dysarthria"],
        "validation": "5-fold GroupKFold by speaker_id (speaker-independent)",
        "n_samples": int(len(df)),
        "n_speakers": int(len(np.unique(groups))),
        "n_features": len(feat_cols),
    }
    print("\nspeaker-independent out-of-fold summary:")
    print(json.dumps(summary, indent=2))

    # final model on ALL data (for optional runtime use / inspection)
    final = new_pipe()
    final.fit(X, y)

    save_bundle(
        MODEL_DIR / "dysarthria_real_torgo.joblib",
        {
            "task": "binary_dysarthria_real_torgo",
            "pipeline": final,
            "feature_columns": feat_cols,
            "classes": [0, 1],
            "target_labels": {"0": "healthy", "1": "dysarthria"},
            "data_source": "TORGO (research dataset)",
            "clinically_validated": False,
            "cv_metrics": summary,
            "fold_metrics": fold_rows,
        },
    )
    METRICS_JSON.write_text(
        json.dumps({"summary": summary, "folds": fold_rows}, indent=2),
        encoding="utf-8",
    )
    print(f"  saved -> {METRICS_JSON}")
    print("\nDONE. (REAL research data; speaker-independent evaluation)")


if __name__ == "__main__":
    main()
