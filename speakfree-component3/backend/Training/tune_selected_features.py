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


# ---------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------
TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"

INNER_FOLDS = 3
OUTER_FOLDS = 5


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
            "No selected features were found."
        )

    return features


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------
def load_data(selected_features):

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Feature dataset not found:\n"
            f"{DATASET_PATH}"
        )

    df = pd.read_csv(
        DATASET_PATH
    )

    required_columns = {
        TARGET_COLUMN,
        GROUP_COLUMN
    }

    missing_required = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_required:
        raise ValueError(
            f"Missing required columns: "
            f"{missing_required}"
        )

    missing_features = [
        feature
        for feature in selected_features
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Selected features missing from dataset: "
            f"{missing_features}"
        )

    X = df[selected_features].copy()

    y = df[TARGET_COLUMN].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    if y.isnull().any():
        invalid_labels = (
            df.loc[
                y.isnull(),
                TARGET_COLUMN
            ]
            .unique()
            .tolist()
        )

        raise ValueError(
            f"Unexpected labels found: "
            f"{invalid_labels}"
        )

    groups = df[GROUP_COLUMN]

    if groups.nunique() < OUTER_FOLDS:
        raise ValueError(
            f"Only {groups.nunique()} speakers found. "
            f"At least {OUTER_FOLDS} are required."
        )

    return df, X, y, groups


# ---------------------------------------------------------
# Build Random Forest pipeline
# ---------------------------------------------------------
def build_pipeline():

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
# Hyperparameter tuning
# ---------------------------------------------------------
def tune_model(
    X,
    y,
    groups
):

    pipeline = build_pipeline()

    parameter_grid = {

        "classifier__n_estimators": [
            200,
            400,
            600,
            800
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
            "log2",
            0.5
        ]
    }

    inner_cv = GroupKFold(
        n_splits=INNER_FOLDS
    )

    print(
        "\nParameter combinations being tested: "
        f"{4 * 4 * 3 * 3 * 3}"
    )

    print(
        f"Inner validation: "
        f"{INNER_FOLDS}-fold GroupKFold by speaker"
    )

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=parameter_grid,
        scoring="f1",
        cv=inner_cv,
        n_jobs=-1,
        verbose=1,
        refit=True
    )

    print(
        "\nStarting selected-feature tuning..."
    )

    # IMPORTANT:
    # Speaker groups are passed here, NOT into GridSearchCV().
    search.fit(
        X,
        y,
        groups=groups
    )

    print(
        "\nBest parameters:"
    )

    print(
        search.best_params_
    )

    print(
        f"\nBest inner-CV F1: "
        f"{search.best_score_:.4f}"
    )

    return search.best_estimator_, search.best_params_


# ---------------------------------------------------------
# Outer speaker-independent validation
# ---------------------------------------------------------
def validate_model(
    model,
    X,
    y,
    groups
):

    outer_cv = GroupKFold(
        n_splits=OUTER_FOLDS
    )

    print(
        "\nRunning outer speaker-independent validation..."
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
        "=========================================="
    )

    print(
        "COMPONENT 2 - SELECTED FEATURE TUNING"
    )

    print(
        "=========================================="
    )

    print(
        "\nLoading selected features..."
    )

    selected_features = load_selected_features()

    print(
        f"Selected features: "
        f"{len(selected_features)}"
    )

    df, X, y, groups = load_data(
        selected_features
    )

    print(
        f"Samples: {len(df)}"
    )

    print(
        f"Speakers: {groups.nunique()}"
    )

    print(
        "\nClass distribution:"
    )

    print(
        df[TARGET_COLUMN].value_counts()
    )

    # -----------------------------------------------------
    # Hyperparameter tuning
    # -----------------------------------------------------
    best_model, best_params = tune_model(
        X,
        y,
        groups
    )

    # -----------------------------------------------------
    # Outer validation
    # -----------------------------------------------------
    print(
        "\n=========================================="
    )

    print(
        "FINAL OUTER VALIDATION"
    )

    print(
        "=========================================="
    )

    results = validate_model(
        model=best_model,
        X=X,
        y=y,
        groups=groups
    )

    # -----------------------------------------------------
    # Print results
    # -----------------------------------------------------
    print(
        f"\nAccuracy:           "
        f"{results['accuracy']:.4f}"
    )

    print(
        f"Balanced Accuracy:  "
        f"{results['balanced_accuracy']:.4f}"
    )

    print(
        f"Precision:          "
        f"{results['precision']:.4f}"
    )

    print(
        f"Recall:             "
        f"{results['recall']:.4f}"
    )

    print(
        f"F1:                 "
        f"{results['f1']:.4f}"
    )

    print(
        f"ROC-AUC:            "
        f"{results['roc_auc']:.4f}"
    )

    # -----------------------------------------------------
    # Save results
    # -----------------------------------------------------
    output = pd.DataFrame(
        [
            {
                "model":
                    "Tuned Random Forest - "
                    "25 selected features",

                "feature_count":
                    len(selected_features),

                "accuracy":
                    results["accuracy"],

                "balanced_accuracy":
                    results["balanced_accuracy"],

                "precision":
                    results["precision"],

                "recall":
                    results["recall"],

                "f1":
                    results["f1"],

                "roc_auc":
                    results["roc_auc"],

                "inner_cv_f1":
                    None,

                "inner_cv":
                    "3-fold GroupKFold by speaker",

                "outer_cv":
                    "5-fold GroupKFold by speaker",

                "speakers":
                    groups.nunique(),

                "samples":
                    len(df)
            }
        ]
    )

    output_path = (
        OUTPUT_DIR /
        "final_candidate_results.csv"
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

    # -----------------------------------------------------
    # Print final configuration
    # -----------------------------------------------------
    print(
        "\n=========================================="
    )

    print(
        "BEST MODEL CONFIGURATION"
    )

    print(
        "=========================================="
    )

    for parameter, value in best_params.items():

        print(
            f"{parameter}: {value}"
        )


if __name__ == "__main__":
    main()