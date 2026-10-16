from pathlib import Path
import sys


# ---------------------------------------------------------
# Add backend folder to Python path
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIR)
    )


# ---------------------------------------------------------
# Import TextGrid analysis service
# ---------------------------------------------------------
from services.textgrid_analysis import (
    analyze_textgrid
)


# ---------------------------------------------------------
# Project and TextGrid paths
# ---------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parents[2]

TEXTGRID_PATH = (
    PROJECT_DIR
    / "alignment_test"
    / "output"
    / "F01_1_arrayMic_0006.TextGrid"
)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():

    print(
        "Reading MFA TextGrid..."
    )

    print(
        f"TextGrid path: {TEXTGRID_PATH}"
    )

    # Check that the file exists before analysis
    if not TEXTGRID_PATH.exists():

        raise FileNotFoundError(
            f"\nTextGrid file not found:\n"
            f"{TEXTGRID_PATH}\n\n"
            f"Make sure MFA alignment completed successfully."
        )

    result = analyze_textgrid(
        str(TEXTGRID_PATH)
    )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------
    print(
        "\n================================"
    )

    print(
        "PHONEME ALIGNMENT RESULTS"
    )

    print(
        "================================"
    )

    print(
        f"\nPhonemes analyzed: "
        f"{result['timing']['phoneme_count']}"
    )

    print(
        f"Mean phoneme duration: "
        f"{result['timing']['mean_duration']} sec"
    )

    print(
        f"Duration variation: "
        f"{result['timing']['duration_variation']}"
    )

    print(
        f"Timing consistency: "
        f"{result['timing']['timing_consistency_score']}/100"
    )

    # -----------------------------------------------------
    # Alignment reliability
    # -----------------------------------------------------
    print(
        f"\nAlignment reliability: "
        f"{result['alignment']['alignment_reliability']}/100"
    )

    print(
        f"Alignment quality: "
        f"{result['alignment']['quality']}"
    )

    print(
        f"Uncertainty flag: "
        f"{result['alignment']['uncertainty_flag']}"
    )

    # -----------------------------------------------------
    # Phoneme intervals
    # -----------------------------------------------------
    print(
        "\nPhoneme intervals:"
    )

    print(
        "--------------------------------"
    )

    for phoneme in result["phonemes"]:

        print(
            f"{phoneme['phoneme']:>8} | "
            f"{phoneme['start']:.4f} - "
            f"{phoneme['end']:.4f} | "
            f"duration="
            f"{phoneme['duration']:.4f}"
        )

    print(
        "\nAnalysis completed successfully."
    )


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------
if __name__ == "__main__":
    main()