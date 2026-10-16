from pathlib import Path
import sys
import json

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------
# Make backend importable
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
DATASET_PATH = Path(
    "dataset/torgo/features.csv"
)

SELECTED_FEATURES_PATH = Path(
    "dataset/torgo/feature_selection/selected_features.txt"
)

MODEL_DIR = Path(
    "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODEL_PATH = (
    MODEL_DIR /
    "component2_final_model.joblib"
)

MODEL_INFO_PATH = (
    MODEL_DIR /
    "component2_model_info.json"
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
TARGET_COLUMN = "speech_status"


# ---------------------------------------------------------
# Load selected features
# ---------------------------------------------------------
def load_selected_features():

    if not SELECTED_FEATURES_PATH.exists():

        raise FileNotFoundError(
            f"Selected feature file not found:\n"
            f"{SELECTED_FEATURES_PATH}"
        )

    with open(
        SELECTED_FEATURES_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        features = [
            line.strip()
            for line in file
            if line.strip()
        ]

    if not features:

        raise ValueError(
            "No selected features found."
        )

    return features


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    print(
        "=========================================="
    )

    print(
        "COMPONENT 2 FINAL MODEL TRAINING"
    )

    print(
        "=========================================="
    )

    print(
        "\nLoading dataset..."
    )

    df = pd.read_csv(
        DATASET_PATH
    )

    selected_features = (
        load_selected_features()
    )

    print(
        f"Samples: {len(df)}"
    )

    print(
        f"Selected features: "
        f"{len(selected_features)}"
    )

    missing = [
        feature
        for feature in selected_features
        if feature not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing features:\n{missing}"
        )

    X = df[
        selected_features
    ].copy()

    y = df[
        TARGET_COLUMN
    ].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    if y.isnull().any():

        raise ValueError(
            "Invalid speech_status labels found."
        )

    # -----------------------------------------------------
    # Final model
    #
    # This is the best 25-feature configuration
    # established by our previous validation experiment.
    # -----------------------------------------------------
    pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),

            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=None,
                    max_features="log2",
                    min_samples_leaf=1,
                    min_samples_split=2,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1
                )
            )
        ]
    )

    print(
        "\nTraining final model..."
    )

    pipeline.fit(
        X,
        y
    )

    # -----------------------------------------------------
    # Save model bundle
    # -----------------------------------------------------
    model_bundle = {
        "pipeline": pipeline,
        "feature_columns": selected_features,
        "target_labels": {
            "0": "healthy",
            "1": "dysarthria"
        },
        "model_type": (
            "RandomForestClassifier"
        ),
        "feature_count": len(
            selected_features
        ),
        "random_state": 42,
    }

    joblib.dump(
        model_bundle,
        MODEL_PATH
    )

    # -----------------------------------------------------
    # Save model information
    # -----------------------------------------------------
    model_info = {
        "model_type":
            "RandomForestClassifier",

        "feature_count":
            len(selected_features),

        "features":
            selected_features,

        "training_samples":
            len(df),

        "healthy_samples":
            int(
                (y == 0).sum()
            ),

        "dysarthria_samples":
            int(
                (y == 1).sum()
            ),

        "validation_reference": {
            "accuracy": 0.7464,
            "balanced_accuracy": 0.7295,
            "precision": 0.6114,
            "recall": 0.6778,
            "f1": 0.6429,
            "roc_auc": 0.7709
        },

        "important_note": (
            "The stored validation results correspond "
            "to the previously evaluated 25-feature "
            "configuration. Final inference model is "
            "trained on all available labelled samples."
        )
    }

    MODEL_INFO_PATH.write_text(
        json.dumps(
            model_info,
            indent=4
        ),
        encoding="utf-8"
    )

    print(
        "\nFinal model trained successfully."
    )

    print(
        f"Model: {MODEL_PATH}"
    )

    print(
        f"Info: {MODEL_INFO_PATH}"
    )


if __name__ == "__main__":
    main()