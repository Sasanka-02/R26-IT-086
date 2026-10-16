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
    roc_auc_score
)
from sklearn.model_selection import (
    GroupKFold,
    GridSearchCV,
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

OUTPUT_DIR = Path(
    "dataset/torgo/model_tuning"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------
def load_dataset():

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

    groups = df[GROUP_COLUMN]

    return df, X, y, groups, feature_columns


# ---------------------------------------------------------
# Create model pipeline
# ---------------------------------------------------------
def create_pipeline():

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
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1
                )
            )
        ]
    )


# ---------------------------------------------------------
# Tune Random Forest
# ---------------------------------------------------------
def tune_model(
    X,
    y,
    groups
):

    pipeline = create_pipeline()

    parameter_grid = {
        "classifier__n_estimators": [
            200,
            400,
            600
        ],

        "classifier__max_depth": [
            None,
            10,
            20,
            30
        ],

        "classifier__min_samples_split": [
            2,
            5,
            10
        ],

        "classifier__min_samples_leaf": [
            1,
            2,
            4
        ],

        "classifier__max_features": [
            "sqrt",
            "log2"
        ]
    }

    inner_cv = GroupKFold(
        n_splits=3
    )

    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring="f1",
        cv=inner_cv,
        n_jobs=-1,
        verbose=1
    )

    print(
        "\nStarting hyperparameter tuning..."
    )

    grid_search.fit(
        X,
        y,
        groups=groups
    )

    print(
        "\nBest parameters:"
    )

    print(
        grid_search.best_params_
    )

    print(
        f"\nBest inner-CV F1: "
        f"{grid_search.best_score_:.4f}"
    )

    return grid_search.best_estimator_


# ---------------------------------------------------------
# Evaluate tuned model
# ---------------------------------------------------------
def evaluate_model(
    model,
    X,
    y,
    groups
):

    outer_cv = GroupKFold(
        n_splits=5
    )

    predictions = cross_val_predict(
        model,
        X,
        y,
        cv=outer_cv,
        groups=groups,
        method="predict"
    )

    probabilities = cross_val_predict(
        model,
        X,
        y,
        cv=outer_cv,
        groups=groups,
        method="predict_proba"
    )[:, 1]

    results = {
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

    return results


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    print(
        "Loading TORGO feature dataset..."
    )

    df, X, y, groups, feature_columns = load_dataset()

    print(
        f"Samples: {len(df)}"
    )

    print(
        f"Features: {len(feature_columns)}"
    )

    print(
        f"Speakers: {groups.nunique()}"
    )

    print(
        "\n=========================================="
    )

    print(
        "RANDOM FOREST HYPERPARAMETER TUNING"
    )

    print(
        "=========================================="
    )

    best_model = tune_model(
        X,
        y,
        groups
    )

    print(
        "\n=========================================="
    )

    print(
        "EVALUATING TUNED MODEL"
    )

    print(
        "=========================================="
    )

    results = evaluate_model(
        best_model,
        X,
        y,
        groups
    )

    print(
        f"\nAccuracy:           {results['accuracy']:.4f}"
    )

    print(
        f"Balanced Accuracy:  {results['balanced_accuracy']:.4f}"
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

    results_df = pd.DataFrame(
        [
            {
                "model": "Tuned Random Forest",
                **results
            }
        ]
    )

    output_path = (
        OUTPUT_DIR /
        "tuned_random_forest_results.csv"
    )

    results_df.to_csv(
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