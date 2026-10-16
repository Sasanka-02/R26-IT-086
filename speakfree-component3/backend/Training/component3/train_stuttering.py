"""
train_stuttering.py
===================

Trains the MULTI-LABEL stuttering-event classifier:
    repetition / prolongation / block   (each independently 0/1)

Model  : MultiOutputClassifier(RandomForestClassifier(class_weight="balanced"))
Dataset: SYNTHETIC_DEMO  (NOT clinically validated)
Output : Models/component3/stuttering_multilabel.joblib

NOTE ON THE RESEARCH DIRECTION
------------------------------
The final research plan replaces this classical baseline with a HuBERT /
wav2vec2 acoustic model operating on raw audio. The runtime interface in
`component3/stuttering.py` is intentionally model-agnostic so that swap only
touches this training script + the loaded artifact, not the pipeline.
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR  # noqa: F401,E402

import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, hamming_loss
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from component3.common import FEATURE_ORDER, STUTTER_EVENTS, STUTTER_MODEL_PATH
from _trainutil import RANDOM_STATE, load_demo, save_bundle


def main():
    print("=" * 60)
    print("COMPONENT 3 - MULTI-LABEL STUTTERING EVENTS  (DEMO DATA)")
    print("=" * 60)

    df = load_demo()
    X = df[FEATURE_ORDER].to_numpy(dtype=float)
    Y = df[[f"stutter_{e}" for e in STUTTER_EVENTS]].to_numpy(dtype=int)

    X_tr, X_te, Y_tr, Y_te = train_test_split(
        X, Y, test_size=0.25, random_state=RANDOM_STATE
    )
    print(f"train={len(X_tr)}  test={len(X_te)}")
    for i, e in enumerate(STUTTER_EVENTS):
        print(f"  positives[{e}] train={Y_tr[:, i].sum()} test={Y_te[:, i].sum()}")

    base = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "rf",
                RandomForestClassifier(
                    n_estimators=250,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model = MultiOutputClassifier(base, n_jobs=-1)
    model.fit(X_tr, Y_tr)

    pred = model.predict(X_te)
    proba = _proba_matrix(model, X_te)

    per_label_f1 = {
        e: round(float(f1_score(Y_te[:, i], pred[:, i], zero_division=0)), 4)
        for i, e in enumerate(STUTTER_EVENTS)
    }
    macro_f1 = round(float(np.mean(list(per_label_f1.values()))), 4)
    hloss = round(float(hamming_loss(Y_te, pred)), 4)

    print(f"\nper-label F1 : {per_label_f1}")
    print(f"macro F1     : {macro_f1}")
    print(f"hamming loss : {hloss}")

    save_bundle(
        STUTTER_MODEL_PATH,
        {
            "task": "multilabel_stuttering_events",
            "model": model,
            "labels": STUTTER_EVENTS,
            "data_source": "SYNTHETIC_DEMO",
            "clinically_validated": False,
            "metrics": {
                "per_label_f1": per_label_f1,
                "macro_f1": macro_f1,
                "hamming_loss": hloss,
                "n_train": int(len(X_tr)),
                "n_test": int(len(X_te)),
            },
        },
    )
    print("\nDONE. (DEMO model - not a clinical result)")


def _proba_matrix(model, X):
    cols = []
    for est in model.estimators_:
        p = est.predict_proba(X)
        classes = list(est.named_steps["rf"].classes_)
        cols.append(p[:, classes.index(1)] if 1 in classes else np.zeros(len(X)))
    return np.column_stack(cols)


if __name__ == "__main__":
    main()
