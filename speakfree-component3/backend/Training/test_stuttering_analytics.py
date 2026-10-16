from pathlib import Path
import sys

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BACKEND_DIR)
    )

from services.stuttering_analytics import (
    analyze_stuttering
)


def main():

    print(
        "=========================================="
    )

    print(
        "STUTTERING / FLUENCY ANALYSIS TEST"
    )

    print(
        "=========================================="
    )

    test_text = (
        "I I I want to go "
        "um um I want to go"
    )

    test_segments = [
        {
            "start": 0.0,
            "end": 1.0
        },
        {
            "start": 1.8,
            "end": 2.7
        },
        {
            "start": 3.9,
            "end": 4.8
        }
    ]

    result = analyze_stuttering(
        recognized_text=test_text,
        segments=test_segments
    )

    print(
        "\nFluency score:"
    )

    print(
        result[
            "fluency"
        ][
            "fluency_score"
        ]
    )

    print(
        "\nWord repetitions:"
    )

    print(
        len(
            result[
                "word_repetitions"
            ]
        )
    )

    print(
        "\nPhrase repetitions:"
    )

    print(
        len(
            result[
                "phrase_repetitions"
            ]
        )
    )

    print(
        "\nFillers:"
    )

    print(
        len(
            result[
                "fillers_and_hesitations"
            ]
        )
    )

    print(
        "\nSpeech rate:"
    )

    print(
        result[
            "speech_rate"
        ][
            "words_per_minute"
        ],
        "WPM"
    )

    print(
        "\nInterpretation:"
    )

    print(
        result[
            "fluency"
        ][
            "interpretation"
        ]
    )


if __name__ == "__main__":
    main()