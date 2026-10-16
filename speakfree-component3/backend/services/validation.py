import numpy as np
import pandas as pd

from scipy.stats import spearmanr

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)
from sklearn.model_selection import (
    GroupKFold,
    cross_val_predict
)
from sklearn.pipeline import Pipeline


def validate_classification_model(
    dataframe: pd.DataFrame,
    target_column: str = "speech_status",
    speaker_column: str = "speaker_id",
    folds: int = 5
):

    excluded_columns = {
        target_column,
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

    # Convert healthy/dysarthria to binary labels
    y = (
        dataframe[target_column]
        .map(
            {
                "healthy": 0,
                "dysarthria": 1
            }
        )
    )

    if y.isnull().any():
        raise ValueError(
            "Unexpected labels found in speech_status."
        )

    groups = dataframe[speaker_column]

    if groups.nunique() < folds:
        raise ValueError(
            f"Only {groups.nunique()} speakers available. "
            f"Need at least {folds} speakers."
        )

    pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="median")
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    random_state=42,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    n_jobs=-1
                )
            )
        ]
    )

    cv = GroupKFold(
        n_splits=folds
    )

    predictions = cross_val_predict(
        pipeline,
        X,
        y,
        cv=cv,
        groups=groups,
        method="predict"
    )

    probabilities = cross_val_predict(
        pipeline,
        X,
        y,
        cv=cv,
        groups=groups,
        method="predict_proba"
    )[:, 1]

    accuracy = accuracy_score(
        y,
        predictions
    )

    balanced_accuracy = balanced_accuracy_score(
        y,
        predictions
    )

    precision = precision_score(
        y,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y,
        predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y,
        probabilities
    )

    matrix = confusion_matrix(
        y,
        predictions
    )

    report = classification_report(
        y,
        predictions,
        target_names=[
            "healthy",
            "dysarthria"
        ],
        zero_division=0
    )

    return {
        "accuracy": round(
            float(accuracy),
            4
        ),
        "balanced_accuracy": round(
            float(balanced_accuracy),
            4
        ),
        "precision": round(
            float(precision),
            4
        ),
        "recall": round(
            float(recall),
            4
        ),
        "f1_score": round(
            float(f1),
            4
        ),
        "roc_auc": round(
            float(roc_auc),
            4
        ),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "speakers": int(
            groups.nunique()
        ),
        "samples": int(
            len(dataframe)
        ),
        "features": int(
            len(feature_columns)
        ),
        "validation_method": (
            "5-fold GroupKFold by speaker"
        )
    }