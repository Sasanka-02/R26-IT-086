from pathlib import Path

import pandas as pd

from services.articulation_model import ArticulationModel


DATASET_PATH = Path(
    "dataset/torgo/features.csv"
)

TARGET_COLUMN = "speech_status"


def main():

    print("Loading feature dataset...")

    dataframe = pd.read_csv(
        DATASET_PATH
    )

    print(
        f"Dataset shape: {dataframe.shape}"
    )

    print("\nClass distribution:")
    print(
        dataframe[TARGET_COLUMN].value_counts()
    )

    print("\nTraining model...")

    model = ArticulationModel()

    model.train(
        dataframe=dataframe,
        target_column=TARGET_COLUMN
    )

    model.save()

    print("\nModel trained successfully.")

    print("\nTop 20 important features:")

    importance = model.get_feature_importance()

    print(
        importance.head(20).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()