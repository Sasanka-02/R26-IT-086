"""
evaluate.py
===========

Prints a consolidated evaluation report for every trained Component 3 model
using the metrics stored in each model bundle at training time.

    python training/evaluate.py
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR  # noqa: F401,E402

import json  # noqa: E402

import joblib  # noqa: E402

from component3.common import (
    DISORDER_MODEL_PATH,
    SEVERITY_MODEL_PATH,
    STUTTER_MODEL_PATH,
    DYSARTHRIA_REAL_MODEL_PATH,
    MODEL_CARD_PATH,
)


def _show(path, title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    if not path.exists():
        print(f"  NOT TRAINED YET ({path.name}). Run train_all.py")
        return
    b = joblib.load(path)
    print(f"  data_source          : {b.get('data_source')}")
    print(f"  clinically_validated : {b.get('clinically_validated')}")
    print(f"  trained_at           : {b.get('trained_at')}")
    metrics = b.get("metrics") or b.get("cv_metrics") or {}
    print(json.dumps(metrics, indent=2))


def main():
    _show(DISORDER_MODEL_PATH, "MULTI-DISORDER CLASSIFIER  (DEMO)")
    _show(SEVERITY_MODEL_PATH, "SEVERITY ESTIMATOR L1-L4  (DEMO)")
    _show(STUTTER_MODEL_PATH, "STUTTERING MULTI-LABEL  (DEMO)")
    _show(DYSARTHRIA_REAL_MODEL_PATH, "DYSARTHRIA MODEL  (REAL - TORGO, speaker-independent)")

    print("\n" + "=" * 60)
    print("MODEL CARD")
    print("=" * 60)
    if MODEL_CARD_PATH.exists():
        print(MODEL_CARD_PATH.read_text(encoding="utf-8"))
    else:
        print("  model_card.json not found - run train_all.py")


if __name__ == "__main__":
    main()
