from pathlib import Path
import sys

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GroupKFold


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
    "dataset/torgo/feature_analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TARGET_COLUMN = "speech_status"
GROUP_COLUMN = "speaker_id"


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
def load_data():

    df = pd.read_csv(DATASET_PATH)

    print("Dataset loaded")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df


# ---------------------------------------------------------
# Identify numeric features
# ---------------------------------------------------------
def get_numeric_features(df):

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

    return feature_columns


# ---------------------------------------------------------
# Analyze basic feature properties
# ---------------------------------------------------------
def analyze_basic_properties(
    df,
    feature_columns
):

    results = []

    for feature in feature_columns:

        values = df[feature]

        results.append(
            {
                "feature": feature,
                "variance": float(
                    values.var()
                ),
                "unique_values": int(
                    values.nunique()
                ),
                "missing_values": int(
                    values.isna().sum()
                ),
                "mean": float(
                    values.mean()
                ),
                "std": float(
                    values.std()
                ),
                "min": float(
                    values.min()
                ),
                "max": float(
                    values.max()
                )
            }
        )

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        by="variance",
        ascending=False
    )

    output_path = (
        OUTPUT_DIR /
        "feature_statistics.csv"
    )

    result_df.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nFeature statistics saved to:\n{output_path}"
    )

    return result_df


# ---------------------------------------------------------
# Find highly correlated features
# ---------------------------------------------------------
def find_correlated_features(
    df,
    feature_columns,
    threshold=0.95
):

    correlation_matrix = df[
        feature_columns
    ].corr().abs()

    upper_triangle = correlation_matrix.where(
        np.triu(
            np.ones(
                correlation_matrix.shape
            ),
            k=1
        ).astype(bool)
    )

    correlated_pairs = []

    for column in upper_triangle.columns:

        for row in upper_triangle.index:

            value = upper_triangle.loc[
                row,
                column
            ]

            if pd.notna(value) and value >= threshold:

                correlated_pairs.append(
                    {
                        "feature_1": row,
                        "feature_2": column,
                        "correlation": float(value)
                    }
                )

    result_df = pd.DataFrame(
        correlated_pairs
    )

    output_path = (
        OUTPUT_DIR /
        "high_correlations.csv"
    )

    result_df.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nHighly correlated feature pairs: "
        f"{len(result_df)}"
    )

    print(
        f"Saved to:\n{output_path}"
    )

    if len(result_df) > 0:

        print(
            "\nTop correlated pairs:"
        )

        print(
            result_df
            .sort_values(
                "correlation",
                ascending=False
            )
            .head(20)
            .to_string(
                index=False
            )
        )


# ---------------------------------------------------------
# Train exploratory Random Forest
# ---------------------------------------------------------
def analyze_model_importance(
    df,
    feature_columns
):

    X = df[feature_columns]

    y = df[TARGET_COLUMN].map(
        {
            "healthy": 0,
            "dysarthria": 1
        }
    )

    groups = df[GROUP_COLUMN]

    pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=300,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1
                )
            )
        ]
    )

    # Fit on complete dataset ONLY for exploratory
    # feature importance analysis.
    pipeline.fit(
        X,
        y
    )

    classifier = pipeline.named_steps[
        "model"
    ]

    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance":
                classifier.feature_importances_
        }
    )

    importance_df = importance_df.sort_values(
        by="importance",
        ascending=False
    )

    output_path = (
        OUTPUT_DIR /
        "random_forest_feature_importance.csv"
    )

    importance_df.to_csv(
        output_path,
        index=False
    )

    print(
        "\nTop 20 Random Forest features:"
    )

    print(
        importance_df.head(20)
        .to_string(index=False)
    )

    print(
        f"\nSaved to:\n{output_path}"
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    df = load_data()

    feature_columns = get_numeric_features(
        df
    )

    print(
        f"\nNumeric features: "
        f"{len(feature_columns)}"
    )

    print(
        "\nAnalyzing feature statistics..."
    )

    analyze_basic_properties(
        df,
        feature_columns
    )

    print(
        "\nChecking highly correlated features..."
    )

    find_correlated_features(
        df,
        feature_columns
    )

    print(
        "\nAnalyzing Random Forest feature importance..."
    )

    analyze_model_importance(
        df,
        feature_columns
    )

    print(
        "\n================================"
    )

    print(
        "FEATURE ANALYSIS COMPLETED"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()