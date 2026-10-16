"""
tune_dysarthria_real_torgo.py
=============================

Hyper-parameter tuning + probability calibration for the stage-1 REAL-DATA model (TORGO).

Leakage-safe NESTED cross-validation, speaker-independent at both levels:

    outer loop  5-fold GroupKFold by speaker  (the SAME folds as train_dysarthria_real_torgo.py,
                so the tuned and baseline scores are directly comparable)
    inner loop  3-fold GroupKFold by speaker on the outer-training speakers only:
                RandomizedSearchCV over the RandomForest settings, scored by balanced accuracy
    calibration sigmoid (Platt) calibration fitted with inner speaker folds - the stage-1
                probability is averaged over windows and fed to stage 2, so calibration matters

The tuned configuration is adopted ONLY if its nested out-of-fold balanced accuracy beats the
baseline without a lower ROC-AUC. It is then written to data/torgo/tuned_params.json, which
train_dysarthria_real_torgo.py (and therefore train_all.py) picks up.

    python training/tune_dysarthria_real_torgo.py        # ~10-20 min on a laptop CPU
    python training/train_all.py                         # rebuild all models with the result
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import TORGO_FEATURES_CSV, TORGO_TUNED_PARAMS  # noqa: E402

import json  # noqa: E402
import time  # noqa: E402
from datetime import datetime  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, f1_score, roc_auc_score  # noqa: E402
from sklearn.model_selection import GroupKFold, RandomizedSearchCV  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402

from _trainutil import RANDOM_STATE  # noqa: E402
from train_dysarthria_real_torgo import LABEL_MAP, TARGET, _feature_columns  # noqa: E402

SEARCH_SPACE = {
    "classifier__n_estimators": [200, 300, 500],
    "classifier__max_depth": [None, 8, 12, 16, 24],
    "classifier__min_samples_leaf": [1, 2, 5, 10, 20, 40, 80],
    "classifier__max_features": ["sqrt", 0.3, 0.5, 0.8],
    "classifier__class_weight": ["balanced", "balanced_subsample"],
}
N_ITER = 24
INNER_SPLITS = 3


def make_pipe(**rf) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1, **rf)),
    ])


def baseline_pipe() -> Pipeline:
    return make_pipe(n_estimators=300, class_weight="balanced")


def search(X, y, groups) -> dict:
    rs = RandomizedSearchCV(
        make_pipe(), SEARCH_SPACE, n_iter=N_ITER, scoring="balanced_accuracy",
        cv=GroupKFold(n_splits=INNER_SPLITS), random_state=RANDOM_STATE, n_jobs=1, refit=False,
    )
    rs.fit(X, y, groups=groups)
    return {k.replace("classifier__", ""): v for k, v in rs.best_params_.items()}


def calibrated(params: dict, X, y, groups):
    splits = list(GroupKFold(n_splits=INNER_SPLITS).split(X, y, groups))
    model = CalibratedClassifierCV(make_pipe(**params), method="sigmoid", cv=splits)
    return model.fit(X, y)


def metrics(y, pred, proba) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, pred)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, proba)), 4),
        "brier": round(float(brier_score_loss(y, proba)), 4),
    }


def main():
    t0 = time.time()
    df = pd.read_csv(TORGO_FEATURES_CSV)
    df = df[df[TARGET].isin(LABEL_MAP)].copy()
    y = df[TARGET].map(LABEL_MAP).to_numpy()
    groups = df["speaker_id"].to_numpy()
    cols = _feature_columns(df)
    X = df[cols].to_numpy(dtype=float)
    print(f"samples={len(y)} features={len(cols)} speakers={len(set(groups))}")

    outer = list(GroupKFold(n_splits=5).split(X, y, groups))
    oof = {name: np.zeros(len(y)) for name in ("baseline", "tuned", "tuned_calibrated")}
    fold_rows = []
    for k, (tr, te) in enumerate(outer, start=1):
        tf = time.time()
        base = baseline_pipe().fit(X[tr], y[tr])
        oof["baseline"][te] = base.predict_proba(X[te])[:, 1]
        best = search(X[tr], y[tr], groups[tr])
        tuned = make_pipe(**best).fit(X[tr], y[tr])
        oof["tuned"][te] = tuned.predict_proba(X[te])[:, 1]
        oof["tuned_calibrated"][te] = calibrated(best, X[tr], y[tr], groups[tr]).predict_proba(X[te])[:, 1]
        row = {"fold": k, "test_speakers": sorted(set(groups[te].tolist())), "best_params": best}
        for name in oof:
            row[name] = metrics(y[te], (oof[name][te] >= 0.5).astype(int), oof[name][te])
        fold_rows.append(row)
        print(f"fold {k} ({time.time() - tf:.0f}s) best={best}")
        for name in oof:
            print(f"   {name:17s} {row[name]}")

    summary = {name: metrics(y, (p >= 0.5).astype(int), p) for name, p in oof.items()}
    print("\nnested speaker-independent OOF summary:")
    for name, m in summary.items():
        print(f"   {name:17s} {m}")

    base, tuned = summary["baseline"], summary["tuned"]
    adopt = tuned["balanced_accuracy"] > base["balanced_accuracy"] and tuned["roc_auc"] >= base["roc_auc"] - 0.005
    calibrate = adopt and summary["tuned_calibrated"]["brier"] < tuned["brier"] \
        and summary["tuned_calibrated"]["roc_auc"] >= tuned["roc_auc"] - 0.005

    final_params = search(X, y, groups) if adopt else None   # selection on ALL speakers for the shipped model
    report = {
        "tuned_at": datetime.now().replace(microsecond=0).isoformat(),
        "method": "nested CV: outer 5-fold GroupKFold by speaker, inner 3-fold GroupKFold RandomizedSearchCV "
                  f"({N_ITER} candidates, balanced accuracy); sigmoid calibration with speaker folds",
        "search_space": {k.replace("classifier__", ""): [str(v) for v in vals] for k, vals in SEARCH_SPACE.items()},
        "nested_oof_summary": summary,
        "folds": fold_rows,
        "adopted": adopt,
        "calibrate": calibrate,
        "params": final_params,
        "runtime_minutes": round((time.time() - t0) / 60, 1),
    }
    TORGO_TUNED_PARAMS.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nadopted={adopt} calibrate={calibrate} params={final_params}")
    print(f"saved -> {TORGO_TUNED_PARAMS}  ({report['runtime_minutes']} min)")


if __name__ == "__main__":
    main()
