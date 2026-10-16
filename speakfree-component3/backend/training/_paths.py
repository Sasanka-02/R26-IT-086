"""
Shared path bootstrap for Component 3 training scripts.

Every training script starts with `from _paths import BACKEND_DIR`, which also inserts the
backend directory onto sys.path so that `import component3.common` works from any cwd.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
BACKEND_DIR = _HERE.parent

for _p in (str(_HERE), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TRAINING_DIR = _HERE
DEMO_DATA_DIR = TRAINING_DIR / "data" / "demo"
DEMO_DATASET_CSV = DEMO_DATA_DIR / "component3_demo_dataset.csv"

TORGO_FEATURES_CSV = TRAINING_DIR / "data" / "torgo" / "features.csv"
TORGO_SELECTED_FEATURES = TRAINING_DIR / "data" / "torgo" / "selected_features.txt"
TORGO_OOF_CSV = TRAINING_DIR / "data" / "torgo" / "oof_probabilities.csv"
TORGO_TUNED_PARAMS = TRAINING_DIR / "data" / "torgo" / "tuned_params.json"  # written by tune_dysarthria_real_torgo.py

DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
