"""
Shared path bootstrap for Component 3 training scripts.

Every training script starts with:

    from _paths import BACKEND_DIR  # noqa

...which also inserts the backend directory onto sys.path so that
`import component3.common` works regardless of the current working directory.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Make both this folder (for sibling imports like `_trainutil`) and the backend
# root (for `import component3.common`) importable, regardless of how the
# script was launched.
for _p in (str(_HERE), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TRAINING_DIR = BACKEND_DIR / "Training" / "component3"
DEMO_DATA_DIR = TRAINING_DIR / "demo_data"
DEMO_DATASET_CSV = DEMO_DATA_DIR / "component3_demo_dataset.csv"

TORGO_FEATURES_CSV = BACKEND_DIR / "dataset" / "torgo" / "features.csv"
TORGO_SELECTED_FEATURES = (
    BACKEND_DIR / "dataset" / "torgo" / "feature_selection" / "selected_features.txt"
)

DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
