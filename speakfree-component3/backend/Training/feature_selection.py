from pathlib import Path
import sys

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------
# Make backend importable
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


DATASET_PATH = Path(
    "dataset/torgo/features.csv"
)

OUTPUT_DIR = Path(
    "dataset/torgo/feature_selection"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TARGET_COLUMN = "speech_status"


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------
def load_data():

    df = pd.read_csv(
        DATASET_PATH
    )

    excluded_columns = {
        TARGET_COLUMN,
        "filename",
        "audio_path",
        "speaker_id",
        "transcription",
        "gender"
    }

    feature_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
        and pd.api.types.is_numeric_dtype(
            df[column]
        )
    ]

    X = df[feature_columns]

    y = df[TARGET_COLUMN].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    return df, X, y, feature_columns


# ---------------------------------------------------------
# Remove exact duplicate / redundant columns
# ---------------------------------------------------------
def remove_manual_redundancy(
    X
):

    columns_to_remove = [
        "duration_seconds",
        "speech_ratio"
    ]

    existing = [
        column
        for column in columns_to_remove
        if column in X.columns
    ]

    X_reduced = X.drop(
        columns=existing
    )

    return X_reduced, existing


# ---------------------------------------------------------
# Model-based feature selection
# ---------------------------------------------------------
def select_features(
    X,
    y
):

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
                    n_estimators=300,
                    random_state=42,
                    class_weight="balanced",
                    min_samples_leaf=2,
                    n_jobs=-1
                )
            )
        ]
    )

    pipeline.fit(
        X,
        y
    )

    classifier = pipeline.named_steps[
        "classifier"
    ]

    feature_importance = pd.DataFrame(
        {
            "feature": X.columns,
            "importance":
                classifier.feature_importances_
        }
    )

    feature_importance = feature_importance.sort_values(
        by="importance",
        ascending=False
    )

    # Keep features with importance above median
    threshold = feature_importance[
        "importance"
    ].median()

    selected_features = feature_importance[
        feature_importance["importance"] >= threshold
    ]["feature"].tolist()

    return (
        selected_features,
        feature_importance
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    print(
        "Loading dataset..."
    )

    df, X, y, feature_columns = load_data()

    print(
        f"Original feature count: "
        f"{len(feature_columns)}"
    )

    # Remove exact redundant variables
    X_reduced, removed = remove_manual_redundancy(
        X
    )

    print(
        f"\nRemoved exact/redundant features:"
    )

    for feature in removed:
        print(
            f"  - {feature}"
        )

    print(
        f"\nRemaining features: "
        f"{len(X_reduced.columns)}"
    )

    # Model-based selection
    selected_features, importance = select_features(
        X_reduced,
        y
    )

    print(
        f"\nSelected features: "
        f"{len(selected_features)}"
    )

    print(
        "\nSelected feature list:"
    )

    for feature in selected_features:
        print(
            f"  - {feature}"
        )

    # Save importance
    importance_path = (
        OUTPUT_DIR /
        "feature_importance.csv"
    )

    importance.to_csv(
        importance_path,
        index=False
    )

    # Save selected list
    selected_path = (
        OUTPUT_DIR /
        "selected_features.txt"
    )

    with open(
        selected_path,
        "w",
        encoding="utf-8"
    ) as file:

        for feature in selected_features:
            file.write(
                feature + "\n"
            )

    print(
        f"\nFeature importance saved to:"
    )

    print(
        importance_path
    )

    print(
        f"\nSelected feature list saved to:"
    )

    print(
        selected_path
    )


if __name__ == "__main__":
    main()