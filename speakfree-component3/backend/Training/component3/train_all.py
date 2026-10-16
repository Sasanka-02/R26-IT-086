"""
train_all.py
============

One command to (re)build every Component 3 model. Run from the backend dir:

    python Training/component3/train_all.py

Steps:
    1. generate the SYNTHETIC_DEMO dataset
    2. train the 4-class disorder classifier      (demo)
    3. train the Level 1-4 severity estimator     (demo)
    4. train the multi-label stuttering model     (demo)
    5. train the REAL TORGO dysarthria model      (research, speaker-independent)
    6. write Models/component3/model_card.json
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import BACKEND_DIR  # noqa: F401,E402

import datetime as dt  # noqa: E402
import json  # noqa: E402

from component3.common import (
    MODEL_CARD_PATH,
    MODEL_VERSION,
    DISORDER_MODEL_PATH,
    SEVERITY_MODEL_PATH,
    STUTTER_MODEL_PATH,
    DYSARTHRIA_REAL_MODEL_PATH,
)

import make_demo_dataset
import train_classifier
import train_severity
import train_stuttering
import train_dysarthria_real_torgo


def _safe(fn, label):
    print("\n" + "#" * 64)
    print(f"# {label}")
    print("#" * 64)
    try:
        fn()
        return True, None
    except Exception as exc:  # keep going so a partial build still helps
        print(f"!! {label} FAILED: {exc!r}")
        return False, repr(exc)


def main():
    results = {}
    results["demo_dataset"] = _safe(make_demo_dataset.main, "1/5 demo dataset")
    results["disorder"] = _safe(train_classifier.main, "2/5 disorder classifier (demo)")
    results["severity"] = _safe(train_severity.main, "3/5 severity estimator (demo)")
    results["stuttering"] = _safe(train_stuttering.main, "4/5 stuttering multi-label (demo)")
    results["dysarthria_real"] = _safe(
        train_dysarthria_real_torgo.main, "5/5 real TORGO dysarthria model"
    )

    card = {
        "component": "Component 3 - Multi-Disorder Severity Classification & Risk Prediction",
        "owner": "I.L.S. Tharushan (IT21315114)",
        "model_version": MODEL_VERSION,
        "built_at": dt.datetime.now().replace(microsecond=0).isoformat(),
        "consumes": "Component 2 output (component2_output / component3_ready_output)",
        "models": {
            "disorder_classifier": {
                "path": DISORDER_MODEL_PATH.name,
                "algorithm": "RandomForestClassifier",
                "data_source": "SYNTHETIC_DEMO",
                "clinically_validated": False,
                "built": results["disorder"][0],
            },
            "severity_estimator": {
                "path": SEVERITY_MODEL_PATH.name,
                "algorithm": "RandomForestClassifier (4 ordered levels)",
                "data_source": "SYNTHETIC_DEMO",
                "clinically_validated": False,
                "built": results["severity"][0],
            },
            "stuttering_multilabel": {
                "path": STUTTER_MODEL_PATH.name,
                "algorithm": "MultiOutputClassifier(RandomForestClassifier)",
                "data_source": "SYNTHETIC_DEMO",
                "clinically_validated": False,
                "built": results["stuttering"][0],
            },
            "dysarthria_real_torgo": {
                "path": DYSARTHRIA_REAL_MODEL_PATH.name,
                "algorithm": "RandomForestClassifier",
                "data_source": "TORGO (research dataset)",
                "validation": "5-fold GroupKFold by speaker (speaker-independent)",
                "clinically_validated": False,
                "built": results["dysarthria_real"][0],
            },
        },
        "disclaimer": (
            "DEMO models are trained on synthetic data to demonstrate the "
            "pipeline and MUST NOT be reported as clinically validated or as "
            "research-valid accuracy. Only the TORGO dysarthria model is "
            "trained on real research data."
        ),
    }
    MODEL_CARD_PATH.write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(f"\nmodel card -> {MODEL_CARD_PATH}")

    ok = all(v[0] for v in results.values())
    print("\n" + ("ALL STEPS OK" if ok else "SOME STEPS FAILED - see log above"))


if __name__ == "__main__":
    main()
