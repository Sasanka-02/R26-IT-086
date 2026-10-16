from pathlib import Path
import sys
import pandas as pd

# Add the backend folder to Python's import path
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.validation import validate_classification_model


DATASET_PATH = "dataset/torgo/features.csv"


def main():

    print("Loading feature dataset...")

    dataframe = pd.read_csv(DATASET_PATH)

    print(
        f"Dataset shape: {dataframe.shape}"
    )

    print(
        "\nRunning speaker-independent validation..."
    )

    results = validate_classification_model(
        dataframe=dataframe,
        target_column="speech_status",
        speaker_column="speaker_id",
        folds=5
    )

    print("\n================================")
    print("COMPONENT 2 MODEL VALIDATION")
    print("================================")

    print(
        f"Accuracy:            {results['accuracy']}"
    )

    print(
        f"Balanced Accuracy:   {results['balanced_accuracy']}"
    )

    print(
        f"Precision:           {results['precision']}"
    )

    print(
        f"Recall:              {results['recall']}"
    )

    print(
        f"F1 Score:            {results['f1_score']}"
    )

    print(
        f"ROC-AUC:             {results['roc_auc']}"
    )

    print(
        f"Speakers:            {results['speakers']}"
    )

    print(
        f"Samples:             {results['samples']}"
    )

    print(
        f"Features:            {results['features']}"
    )

    print(
        "\nValidation method:"
    )

    print(
        results["validation_method"]
    )

    print(
        "\nConfusion Matrix:"
    )

    for row in results["confusion_matrix"]:
        print(row)

    print(
        "\nClassification Report:"
    )

    print(
        results["classification_report"]
    )


if __name__ == "__main__":
    main()