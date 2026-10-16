from pathlib import Path
import csv

from datasets import load_dataset, Audio


OUTPUT_DIR = Path("dataset/torgo")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "metadata.csv"


def get_speaker_id(audio_path: str) -> str:
    """
    Extract the TORGO speaker ID from the filename.

    Examples:
        FC01_1_ARRAYMIC_0066.WAV -> FC01
        F03_1_HEADMIC_0171.WAV   -> F03
        M02_1_ARRAYMIC_0001.WAV  -> M02
        MC01_1_ARRAYMIC_0001.WAV -> MC01
    """

    filename = Path(audio_path).name
    parts = filename.split("_")

    if not parts:
        return "UNKNOWN"

    return parts[0].upper()


def main():

    print("Loading TORGO dataset...")

    dataset = load_dataset(
        "abnerh/TORGO-database",
        split="train"
    )

    print(f"Total records available: {len(dataset)}")

    # We only need metadata at this stage.
    # Disable automatic audio decoding so TorchCodec is not invoked.
    dataset = dataset.cast_column(
        "audio",
        Audio(decode=False)
    )

    records = []

    for index in range(len(dataset)):

        item = dataset[index]

        audio_info = item["audio"]

        audio_path = audio_info.get("path")

        if not audio_path:
            print(
                f"Skipping record {index}: audio path unavailable."
            )
            continue

        speaker_id = get_speaker_id(audio_path)

        record = {
            "dataset_index": index,
            "speaker_id": speaker_id,
            "audio_path": audio_path,
            "transcription": item.get(
                "transcription",
                ""
            ),
            "gender": item.get(
                "gender",
                ""
            ),
            "duration": item.get(
                "duration",
                ""
            ),
            "speech_status": item.get(
                "speech_status",
                ""
            )
        }

        records.append(record)

    if not records:
        raise RuntimeError(
            "No TORGO records were extracted."
        )

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys()
        )

        writer.writeheader()
        writer.writerows(records)

    print()
    print("TORGO metadata created successfully.")
    print(f"Records written: {len(records)}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()