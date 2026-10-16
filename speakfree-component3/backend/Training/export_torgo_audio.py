from pathlib import Path

from datasets import load_dataset, Audio


OUTPUT_DIR = Path("dataset/torgo/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading TORGO dataset...")

    dataset = load_dataset(
        "abnerh/TORGO-database",
        split="train"
    )

    # Do not let Datasets try to decode with TorchCodec.
    dataset = dataset.cast_column(
        "audio",
        Audio(decode=False)
    )

    print(f"Total records: {len(dataset)}")
    print("Exporting audio files...")

    exported = 0
    skipped = 0

    for index in range(len(dataset)):
        item = dataset[index]

        audio_info = item["audio"]

        filename = Path(
            audio_info["path"]
        ).name

        output_path = OUTPUT_DIR / filename

        # If it already exists, don't export again.
        if output_path.exists():
            exported += 1
            continue

        audio_bytes = audio_info.get("bytes")

        if audio_bytes is None:
            print(
                f"[SKIP] No audio bytes available for record {index}: "
                f"{filename}"
            )
            skipped += 1
            continue

        with open(output_path, "wb") as audio_file:
            audio_file.write(audio_bytes)

        exported += 1

        if exported % 100 == 0:
            print(
                f"Exported {exported} / {len(dataset)}"
            )

    print()
    print("Export completed.")
    print(f"Exported: {exported}")
    print(f"Skipped: {skipped}")
    print(f"Audio directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()