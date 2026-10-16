from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Add backend to Python path
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)

from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from sklearn.model_selection import (
    GroupKFold,
    cross_val_predict
)

from sklearn.pipeline import Pipeline

from sklearn.preprocessing import StandardScaler

from sklearn.svm import SVC


DATASET_PATH = Path(
    "dataset/torgo/features.csv"
)

TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"

N_SPLITS = 5


def prepare_data():

    dataframe = pd.read_csv(
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
        for column in dataframe.columns
        if column not in excluded_columns
        and pd.api.types.is_numeric_dtype(
            dataframe[column]
        )
    ]

    X = dataframe[feature_columns]

    y = dataframe[TARGET_COLUMN].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    groups = dataframe[GROUP_COLUMN]

    if y.isnull().any():
        raise ValueError(
            "Unexpected labels found in speech_status."
        )

    if groups.nunique() < N_SPLITS:
        raise ValueError(
            "Not enough unique speakers for GroupKFold."
        )

    return dataframe, X, y, groups, feature_columns


def build_models():

    models = {

        "Logistic Regression": Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="median")
                ),
                (
                    "scaler",
                    StandardScaler()
                ),
                (
                    "classifier",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42
                    )
                )
            ]
        ),

        "Random Forest": Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="median")
                ),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1
                    )
                )
            ]
        ),

        "SVM": Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="median")
                ),
                (
                    "scaler",
                    StandardScaler()
                ),
                (
                    "classifier",
                    SVC(
                        kernel="rbf",
                        probability=True,
                        class_weight="balanced",
                        random_state=42
                    )
                )
            ]
        ),

        "Gradient Boosting": Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="median")
                ),
                (
                    "classifier",
                    GradientBoostingClassifier(
                        n_estimators=200,
                        learning_rate=0.05,
                        max_depth=3,
                        random_state=42
                    )
                )
            ]
        )
    }

    return models


def evaluate_model(
    model,
    X,
    y,
    groups
):

    cv = GroupKFold(
        n_splits=N_SPLITS
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

    return {
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
        )
    }


def main():

    print("Loading dataset...")

    dataframe, X, y, groups, feature_columns = prepare_data()

    print(
        f"Samples: {len(dataframe)}"
    )

    print(
        f"Features: {len(feature_columns)}"
    )

    print(
        f"Speakers: {groups.nunique()}"
    )

    print("\nClass distribution:")

    print(
        y.value_counts()
    )

    models = build_models()

    results = []

    print(
        "\n=========================================="
    )

    print(
        "MODEL COMPARISON"
    )

    print(
        "5-fold GroupKFold by speaker"
    )

    print(
        "==========================================\n"
    )

    for name, model in models.items():

        print(
            f"Evaluating {name}..."
        )

        metrics = evaluate_model(
            model=model,
            X=X,
            y=y,
            groups=groups
        )

        results.append(
            {
                "model": name,
                **metrics
            }
        )

        print(
            f"Accuracy:           {metrics['accuracy']:.4f}"
        )

        print(
            f"Balanced Accuracy:  {metrics['balanced_accuracy']:.4f}"
        )

        print(
            f"Precision:          {metrics['precision']:.4f}"
        )

        print(
            f"Recall:             {metrics['recall']:.4f}"
        )

        print(
            f"F1:                 {metrics['f1']:.4f}"
        )

        print(
            f"ROC-AUC:            {metrics['roc_auc']:.4f}"
        )

        print(
            "------------------------------------------"
        )

    results_df = pd.DataFrame(
        results
    )

    results_df = results_df.sort_values(
        by="f1",
        ascending=False
    )

    print(
        "\n=========================================="
    )

    print(
        "FINAL COMPARISON"
    )

    print(
        "=========================================="
    )

    print(
        results_df.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}"
        )
    )

    output_path = Path(
        "dataset/torgo/model_comparison.csv"
    )

    results_df.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nResults saved to: {output_path}"
    )


if __name__ == "__main__":
    main()