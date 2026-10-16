from pathlib import Path
import sys
import pandas as pd

# Add the backend folder to Python's import path
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.feature_extraction import extract_speech_features


METADATA_PATH = Path("dataset/torgo/metadata.csv")
AUDIO_DIR = Path("dataset/torgo/audio")
OUTPUT_PATH = Path("dataset/torgo/features.csv")


def main():
    print("Loading TORGO metadata...")

    metadata = pd.read_csv(METADATA_PATH)

    print(f"Metadata records: {len(metadata)}")

    rows = []

    for index, row in metadata.iterrows():

        filename = Path(row["audio_path"]).name
        audio_path = AUDIO_DIR / filename

        if not audio_path.exists():
            print(
                f"[SKIP] Audio not found: {filename}"
            )
            continue

        try:
            print(
                f"[{index + 1}/{len(metadata)}] "
                f"Processing {filename}"
            )

            features = extract_speech_features(
                str(audio_path)
            )

            record = {
                "filename": filename,
                "speaker_id": row["speaker_id"],
                "speech_status": row["speech_status"],
                "transcription": row["transcription"],
                "gender": row["gender"],
                "duration": row["duration"],
                **features
            }

            rows.append(record)

        except Exception as error:
            print(
                f"[ERROR] {filename}: {error}"
            )

    if not rows:
        raise RuntimeError(
            "No audio features were extracted."
        )

    feature_dataframe = pd.DataFrame(rows)

    feature_dataframe.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print()
    print("========================================")
    print("Feature extraction completed")
    print("========================================")
    print(f"Records processed: {len(feature_dataframe)}")
    print(f"Features generated: {len(feature_dataframe.columns)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()