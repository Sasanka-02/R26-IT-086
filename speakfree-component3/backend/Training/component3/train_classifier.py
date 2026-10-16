"""
train_classifier.py
===================

Trains the 4-class multi-disorder classifier
(normal / stuttering / dysarthria / articulation).

Dataset : SYNTHETIC_DEMO  (see make_demo_dataset.py - NOT clinically validated)
Model   : RandomForestClassifier (class_weight="balanced", random_state=42)
Split   : stratified train/test (75/25)
Output  : Models/component3/disorder_classifier.joblib
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
)
from sklearn.model_selection import train_test_split

from component3.common import DISORDER_CLASSES, DISORDER_MODEL_PATH, FEATURE_ORDER
from _trainutil import (
    RANDOM_STATE,
    expected_calibration_error,
    load_demo,
    make_rf_pipeline,
    save_bundle,
)


def main():
    print("=" * 60)
    print("COMPONENT 3 - MULTI-DISORDER CLASSIFIER  (DEMO DATA)")
    print("=" * 60)

    df = load_demo()
    X = df[FEATURE_ORDER].to_numpy(dtype=float)
    y = df["disorder"].to_numpy()

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    print(f"train={len(X_tr)}  test={len(X_te)}")

    pipe = make_rf_pipeline(n_estimators=300)
    pipe.fit(X_tr, y_tr)

    pred = pipe.predict(X_te)
    proba = pipe.predict_proba(X_te)
    classes = list(pipe.named_steps["classifier"].classes_)

    acc = accuracy_score(y_te, pred)
    macro_f1 = f1_score(y_te, pred, average="macro")
    cm = confusion_matrix(y_te, pred, labels=DISORDER_CLASSES)
    ece = expected_calibration_error(y_te, proba, classes)

    print(f"\naccuracy      : {acc:.4f}")
    print(f"macro F1      : {macro_f1:.4f}")
    print(f"ECE (top-1)   : {ece:.4f}")
    print("\nclassification report:")
    print(classification_report(y_te, pred, zero_division=0))
    print("confusion matrix (rows=true, cols=pred; order="
          f"{DISORDER_CLASSES}):")
    print(cm)

    save_bundle(
        DISORDER_MODEL_PATH,
        {
            "task": "multi_disorder_classification",
            "pipeline": pipe,
            "classes": classes,
            "data_source": "SYNTHETIC_DEMO",
            "clinically_validated": False,
            "metrics": {
                "accuracy": round(float(acc), 4),
                "macro_f1": round(float(macro_f1), 4),
                "ece_top1": round(float(ece), 4),
                "confusion_matrix": cm.tolist(),
                "confusion_matrix_labels": DISORDER_CLASSES,
                "n_train": int(len(X_tr)),
                "n_test": int(len(X_te)),
            },
        },
    )
    print("\nDONE. (DEMO model - not a clinical result)")


if __name__ == "__main__":
    main()
