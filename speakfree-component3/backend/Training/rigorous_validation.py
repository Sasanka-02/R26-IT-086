from pathlib import Path
import sys

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
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
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------
# Make backend importable
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
DATASET_PATH = Path(
    "dataset/torgo/features.csv"
)

TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"

FOLDS = 5


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

    groups = df[GROUP_COLUMN]

    return df, X, y, groups, feature_columns


# ---------------------------------------------------------
# Create leakage-safe pipeline
# ---------------------------------------------------------
def create_pipeline():

    feature_selector = SelectFromModel(
        estimator=RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
            min_samples_leaf=2,
            n_jobs=-1
        ),
        threshold="median"
    )

    classifier = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        max_features="log2",
        min_samples_leaf=1,
        min_samples_split=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),

            (
                "feature_selection",
                feature_selector
            ),

            (
                "classifier",
                classifier
            )
        ]
    )

    return pipeline


# ---------------------------------------------------------
# Main validation
# ---------------------------------------------------------
def main():

    print(
        "=========================================="
    )

    print(
        "LEAKAGE-SAFE COMPONENT 2 VALIDATION"
    )

    print(
        "=========================================="
    )

    df, X, y, groups, feature_columns = load_data()

    print(
        f"\nSamples: {len(df)}"
    )

    print(
        f"Original features: {len(feature_columns)}"
    )

    print(
        f"Speakers: {groups.nunique()}"
    )

    print(
        "\nUsing:"
    )

    print(
        "5-fold GroupKFold by speaker"
    )

    print(
        "Feature selection performed inside each training fold"
    )

    cv = GroupKFold(
        n_splits=FOLDS
    )

    all_predictions = np.zeros(
        len(y),
        dtype=int
    )

    all_probabilities = np.zeros(
        len(y),
        dtype=float
    )

    fold_results = []

    for fold, (
        train_index,
        test_index
    ) in enumerate(
        cv.split(
            X,
            y,
            groups
        ),
        start=1
    ):

        print(
            f"\nProcessing fold {fold}/{FOLDS}..."
        )

        X_train = X.iloc[
            train_index
        ]

        X_test = X.iloc[
            test_index
        ]

        y_train = y.iloc[
            train_index
        ]

        y_test = y.iloc[
            test_index
        ]

        train_groups = groups.iloc[
            train_index
        ]

        test_groups = groups.iloc[
            test_index
        ]

        pipeline = create_pipeline()

        pipeline.fit(
            X_train,
            y_train
        )

        predictions = pipeline.predict(
            X_test
        )

        probabilities = pipeline.predict_proba(
            X_test
        )[:, 1]

        all_predictions[
            test_index
        ] = predictions

        all_probabilities[
            test_index
        ] = probabilities

        fold_accuracy = accuracy_score(
            y_test,
            predictions
        )

        fold_f1 = f1_score(
            y_test,
            predictions,
            zero_division=0
        )

        fold_auc = roc_auc_score(
            y_test,
            probabilities
        )

        selected_mask = (
            pipeline
            .named_steps[
                "feature_selection"
            ]
            .get_support()
        )

        selected_count = int(
            np.sum(selected_mask)
        )

        fold_results.append(
            {
                "fold": fold,
                "train_speakers":
                    train_groups.nunique(),
                "test_speakers":
                    test_groups.nunique(),
                "selected_features":
                    selected_count,
                "accuracy":
                    fold_accuracy,
                "f1":
                    fold_f1,
                "roc_auc":
                    fold_auc
            }
        )

        print(
            f"Test speakers: "
            f"{test_groups.unique().tolist()}"
        )

        print(
            f"Selected features: "
            f"{selected_count}"
        )

        print(
            f"Accuracy: "
            f"{fold_accuracy:.4f}"
        )

        print(
            f"F1: "
            f"{fold_f1:.4f}"
        )

        print(
            f"ROC-AUC: "
            f"{fold_auc:.4f}"
        )

    # -----------------------------------------------------
    # Overall metrics
    # -----------------------------------------------------
    accuracy = accuracy_score(
        y,
        all_predictions
    )

    balanced_accuracy = balanced_accuracy_score(
        y,
        all_predictions
    )

    precision = precision_score(
        y,
        all_predictions,
        zero_division=0
    )

    recall = recall_score(
        y,
        all_predictions,
        zero_division=0
    )

    f1 = f1_score(
        y,
        all_predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y,
        all_probabilities
    )

    matrix = confusion_matrix(
        y,
        all_predictions
    )

    print(
        "\n=========================================="
    )

    print(
        "OVERALL LEAKAGE-SAFE RESULTS"
    )

    print(
        "=========================================="
    )

    print(
        f"Accuracy:           {accuracy:.4f}"
    )

    print(
        f"Balanced Accuracy:  {balanced_accuracy:.4f}"
    )

    print(
        f"Precision:          {precision:.4f}"
    )

    print(
        f"Recall:             {recall:.4f}"
    )

    print(
        f"F1:                 {f1:.4f}"
    )

    print(
        f"ROC-AUC:            {roc_auc:.4f}"
    )

    print(
        "\nConfusion Matrix:"
    )

    print(
        matrix
    )

    # -----------------------------------------------------
    # Save fold results
    # -----------------------------------------------------
    output_directory = Path(
        "dataset/torgo/validation"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    fold_dataframe = pd.DataFrame(
        fold_results
    )

    fold_path = (
        output_directory /
        "leakage_safe_fold_results.csv"
    )

    fold_dataframe.to_csv(
        fold_path,
        index=False
    )

    summary = pd.DataFrame(
        [
            {
                "accuracy":
                    accuracy,
                "balanced_accuracy":
                    balanced_accuracy,
                "precision":
                    precision,
                "recall":
                    recall,
                "f1":
                    f1,
                "roc_auc":
                    roc_auc,
                "samples":
                    len(df),
                "speakers":
                    groups.nunique(),
                "original_features":
                    len(feature_columns),
                "validation":
                    "5-fold GroupKFold",
                "feature_selection":
                    "inside each training fold"
            }
        ]
    )

    summary_path = (
        output_directory /
        "leakage_safe_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False
    )

    print(
        f"\nFold results saved to:"
    )

    print(
        fold_path
    )

    print(
        f"\nSummary saved to:"
    )

    print(
        summary_path
    )


if __name__ == "__main__":
    main()