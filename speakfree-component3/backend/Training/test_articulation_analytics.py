from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIR)
    )


from services.textgrid_analysis import parse_textgrid
from services.articulation_analytics import (
    analyze_articulation
)


PROJECT_DIR = Path(__file__).resolve().parents[2]

TEXTGRID_PATH = (
    PROJECT_DIR
    / "alignment_test"
    / "output"
    / "F01_1_arrayMic_0006.TextGrid"
)


def main():

    print(
        "Loading MFA alignment..."
    )

    phonemes = parse_textgrid(
        str(TEXTGRID_PATH)
    )

    # Temporary probability for pipeline testing.
    # This will later come from your trained ML model.
    dysarthria_probability = 0.70

    result = analyze_articulation(
        phonemes=phonemes,
        dysarthria_probability=dysarthria_probability
    )

    print(
        "\n================================"
    )

    print(
        "COMPONENT 2 ARTICULATION ANALYTICS"
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
        f"{result['timing']['mean_phoneme_duration']} sec"
    )

    print(
        f"Duration variation: "
        f"{result['timing']['duration_variation']}"
    )

    print(
        f"Timing consistency: "
        f"{result['subscores']['timing_consistency']}/100"
    )

    print(
        f"Phoneme consistency: "
        f"{result['subscores']['phoneme_consistency']}/100"
    )

    print(
        f"Overall articulation indicator: "
        f"{result['subscores']['overall_articulation_indicator']}/100"
    )

    print(
        f"\nInterpretation: "
        f"{result['subscores']['interpretation']}"
    )

    print(
        "\nTiming irregularities:"
    )

    print(
        result["irregularities"]["irregular_count"]
    )

    print(
        "\nFindings:"
    )

    for finding in result["findings"]:
        print(
            f"- {finding}"
        )

    print(
        "\nPhonemes:"
    )

    for phoneme in phonemes:

        print(
            f"{phoneme['phoneme']:>6} | "
            f"{phoneme['start']:.4f} - "
            f"{phoneme['end']:.4f} | "
            f"{phoneme['duration']:.4f}s"
        )


if __name__ == "__main__":
    main()