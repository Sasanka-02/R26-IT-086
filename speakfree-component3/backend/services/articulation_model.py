from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "articulation_classifier.joblib"


class ArticulationModel:

    def __init__(self):

        self.pipeline = Pipeline(
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

        self.feature_columns = []
        self.is_trained = False

    def train(
        self,
        dataframe: pd.DataFrame,
        target_column: str
    ):

        if target_column not in dataframe.columns:
            raise ValueError(
                f"Target column '{target_column}' not found."
            )

        excluded_columns = {
            target_column,
            "filename",
            "audio_path",
            "speaker_id",
            "transcription",
            "gender"
        }

        self.feature_columns = [
            column
            for column in dataframe.columns
            if column not in excluded_columns
            and pd.api.types.is_numeric_dtype(
                dataframe[column]
            )
        ]

        if not self.feature_columns:
            raise ValueError(
                "No numeric feature columns were found."
            )

        X = dataframe[self.feature_columns]
        y = dataframe[target_column]

        self.pipeline.fit(X, y)

        self.is_trained = True

    def predict(self, features: dict):

        if not self.is_trained:
            raise RuntimeError(
                "Model has not been trained."
            )

        input_data = pd.DataFrame(
            [[
                features.get(column)
                for column in self.feature_columns
            ]],
            columns=self.feature_columns
        )

        probabilities = self.pipeline.predict_proba(
            input_data
        )[0]

        classes = list(
            self.pipeline
            .named_steps["classifier"]
            .classes_
        )

        probability_map = {
            str(label): float(probability)
            for label, probability
            in zip(classes, probabilities)
        }

        dysarthria_probability = probability_map.get(
            "dysarthria",
            0.0
        )

        healthy_probability = probability_map.get(
            "healthy",
            0.0
        )

        predicted_class = self.pipeline.predict(
            input_data
        )[0]

        return {
            "predicted_class": str(predicted_class),
            "healthy_probability": round(
                healthy_probability,
                4
            ),
            "dysarthria_probability": round(
                dysarthria_probability,
                4
            ),
            "articulation_risk_score": round(
                dysarthria_probability * 100,
                2
            )
        }

    def save(self):

        if not self.is_trained:
            raise RuntimeError(
                "Cannot save an untrained model."
            )

        MODEL_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        joblib.dump(
            {
                "pipeline": self.pipeline,
                "feature_columns": self.feature_columns
            },
            MODEL_PATH
        )

        print(
            f"Model saved to: {MODEL_PATH}"
        )

    def load(self):

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found: {MODEL_PATH}"
            )

        saved_model = joblib.load(
            MODEL_PATH
        )

        self.pipeline = saved_model["pipeline"]
        self.feature_columns = saved_model[
            "feature_columns"
        ]

        self.is_trained = True

    def get_feature_importance(self):

        if not self.is_trained:
            raise RuntimeError(
                "Model must be trained first."
            )

        classifier = self.pipeline.named_steps[
            "classifier"
        ]

        importance = pd.DataFrame(
            {
                "feature": self.feature_columns,
                "importance": classifier.feature_importances_
            }
        )

        return importance.sort_values(
            by="importance",
            ascending=False
        )