"""
train_severity.py
=================

Trains the severity estimator: Level 1 (Normal) .. Level 4 (Severe).

Approach : RandomForestClassifier over the 4 ordered levels.
           (A plain classifier is used rather than full ordinal regression to
           keep today's implementation robust; the severity probabilities are
           still returned so an ordinal decoding can be layered on later.)

Dataset  : SYNTHETIC_DEMO  (NOT clinically validated)
Output   : models/severity_estimator.joblib
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR  # noqa: F401,E402

import numpy as np  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
)
from sklearn.model_selection import train_test_split

from component3.common import FEATURE_ORDER, SEVERITY_LEVELS, SEVERITY_MODEL_PATH
from _trainutil import (
    RANDOM_STATE,
    expected_calibration_error,
    load_demo,
    make_rf_pipeline,
    save_bundle,
)


def main():
    print("=" * 60)
    print("COMPONENT 3 - SEVERITY ESTIMATOR (Level 1-4)  (DEMO DATA)")
    print("=" * 60)

    df = load_demo()
    X = df[FEATURE_ORDER].to_numpy(dtype=float)
    y = df["severity_level"].to_numpy(dtype=int)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    print(f"train={len(X_tr)}  test={len(X_te)}")

    pipe = make_rf_pipeline(n_estimators=300)
    pipe.fit(X_tr, y_tr)

    pred = pipe.predict(X_te)
    proba = pipe.predict_proba(X_te)
    classes = [int(c) for c in pipe.named_steps["classifier"].classes_]

    acc = accuracy_score(y_te, pred)
    macro_f1 = f1_score(y_te, pred, average="macro")
    mae = mean_absolute_error(y_te, pred)  # ordinal-aware error
    off_by_one = float(np.mean(np.abs(pred - y_te) <= 1))
    cm = confusion_matrix(y_te, pred, labels=SEVERITY_LEVELS)
    ece = expected_calibration_error(y_te, proba, classes)

    print(f"\naccuracy        : {acc:.4f}")
    print(f"macro F1        : {macro_f1:.4f}")
    print(f"MAE (levels)    : {mae:.4f}")
    print(f"within +/-1 lvl : {off_by_one:.4f}")
    print(f"ECE (top-1)     : {ece:.4f}")
    print("\nclassification report:")
    print(classification_report(y_te, pred, zero_division=0))
    print(f"confusion matrix (rows=true, cols=pred; levels {SEVERITY_LEVELS}):")
    print(cm)

    save_bundle(
        SEVERITY_MODEL_PATH,
        {
            "task": "severity_estimation_level_1_4",
            "pipeline": pipe,
            "classes": classes,
            "data_source": "SYNTHETIC_DEMO",
            "clinically_validated": False,
            "metrics": {
                "accuracy": round(float(acc), 4),
                "macro_f1": round(float(macro_f1), 4),
                "mae_levels": round(float(mae), 4),
                "within_one_level": round(off_by_one, 4),
                "ece_top1": round(float(ece), 4),
                "confusion_matrix": cm.tolist(),
                "confusion_matrix_labels": SEVERITY_LEVELS,
                "n_train": int(len(X_tr)),
                "n_test": int(len(X_te)),
            },
        },
    )
    print("\nDONE. (DEMO model - not a clinical result)")


if __name__ == "__main__":
    main()
