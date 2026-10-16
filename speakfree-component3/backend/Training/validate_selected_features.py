from pathlib import Path
import sys

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)
from sklearn.model_selection import (
    GroupKFold,
    cross_val_predict
)
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

OUTPUT_DIR = Path(
    "dataset/torgo/feature_selection"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"


# ---------------------------------------------------------
# Load selected features
# ---------------------------------------------------------
def load_selected_features():

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

    return features


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------
def load_data(
    selected_features
):

    df = pd.read_csv(
        DATASET_PATH
    )

    missing_features = [
        feature
        for feature in selected_features
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing selected features: "
            f"{missing_features}"
        )

    X = df[selected_features]

    y = df[TARGET_COLUMN].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    groups = df[GROUP_COLUMN]

    return df, X, y, groups


# ---------------------------------------------------------
# Create tuned Random Forest
# ---------------------------------------------------------
def create_model():

    return Pipeline(
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


# ---------------------------------------------------------
# Validate
# ---------------------------------------------------------
def validate_model(
    model,
    X,
    y,
    groups
):

    cv = GroupKFold(
        n_splits=5
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
        method="predict"
    )

    probabilities = cross_val_predict(
        model,
        X,
        y,
        cv=cv,
        groups=groups,
        method="predict_proba"
    )[:, 1]

    metrics = {
        "accuracy": accuracy_score(
            y,
            predictions
        ),

        "balanced_accuracy": balanced_accuracy_score(
            y,
            predictions
        ),

        "precision": precision_score(
            y,
            predictions,
            zero_division=0
        ),

        "recall": recall_score(
            y,
            predictions,
            zero_division=0
        ),

        "f1": f1_score(
            y,
            predictions,
            zero_division=0
        ),

        "roc_auc": roc_auc_score(
            y,
            probabilities
        ),

        "confusion_matrix": confusion_matrix(
            y,
            predictions
        ).tolist()
    }

    return metrics


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    print(
        "Loading selected features..."
    )

    selected_features = load_selected_features()

    print(
        f"Selected feature count: "
        f"{len(selected_features)}"
    )

    print(
        "\nSelected features:"
    )

    for feature in selected_features:
        print(
            f"  - {feature}"
        )

    df, X, y, groups = load_data(
        selected_features
    )

    print(
        f"\nSamples: {len(df)}"
    )

    print(
        f"Speakers: {groups.nunique()}"
    )

    print(
        "\nStarting speaker-independent validation..."
    )

    model = create_model()

    results = validate_model(
        model=model,
        X=X,
        y=y,
        groups=groups
    )

    print(
        "\n======================================"
    )

    print(
        "SELECTED FEATURE MODEL RESULTS"
    )

    print(
        "======================================"
    )

    print(
        f"Accuracy:           {results['accuracy']:.4f}"
    )

    print(
        f"Balanced Accuracy:  "
        f"{results['balanced_accuracy']:.4f}"
    )

    print(
        f"Precision:          {results['precision']:.4f}"
    )

    print(
        f"Recall:             {results['recall']:.4f}"
    )

    print(
        f"F1:                 {results['f1']:.4f}"
    )

    print(
        f"ROC-AUC:            {results['roc_auc']:.4f}"
    )

    print(
        "\nConfusion Matrix:"
    )

    for row in results["confusion_matrix"]:
        print(row)

    output = pd.DataFrame(
        [
            {
                "model": "Tuned Random Forest - Selected Features",
                "feature_count": len(selected_features),
                "accuracy": results["accuracy"],
                "balanced_accuracy": results["balanced_accuracy"],
                "precision": results["precision"],
                "recall": results["recall"],
                "f1": results["f1"],
                "roc_auc": results["roc_auc"]
            }
        ]
    )

    output_path = (
        OUTPUT_DIR /
        "selected_feature_validation.csv"
    )

    output.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nResults saved to:"
    )

    print(
        output_path
    )


if __name__ == "__main__":
    main()