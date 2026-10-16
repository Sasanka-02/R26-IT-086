from pathlib import Path
import re
import statistics


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
SILENCE_LABELS = {
    "",
    "sil",
    "sp",
    "spn",
    "silence",
}


# ---------------------------------------------------------
# Parse MFA TextGrid
# ---------------------------------------------------------
def parse_textgrid(textgrid_path: str):
    """
    Parse the MFA phone tier from a Praat TextGrid.

    Returns a list of dictionaries containing:
        phoneme
        start
        end
        duration

    Silence intervals are excluded.
    """

    path = Path(textgrid_path)

    if not path.exists():
        raise FileNotFoundError(
            f"TextGrid not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # Find all TextGrid item blocks
    # -----------------------------------------------------
    tier_blocks = re.findall(
        r'item\s*\[\d+\]\s*:\s*(.*?)(?=\n\s*item\s*\[\d+\]\s*:|\Z)',
        content,
        flags=re.DOTALL
    )

    phone_block = None

    # -----------------------------------------------------
    # Find phone/phoneme tier
    # -----------------------------------------------------
    for block in tier_blocks:

        name_match = re.search(
            r'name\s*=\s*"([^"]*)"',
            block
        )

        if not name_match:
            continue

        tier_name = (
            name_match.group(1)
            .strip()
            .lower()
        )

        if tier_name in {
            "phones",
            "phone",
            "phonemes",
            "phoneme",
        }:
            phone_block = block
            break

    if phone_block is None:

        raise ValueError(
            "Could not find a phone/phoneme tier "
            "in the MFA TextGrid."
        )

    # -----------------------------------------------------
    # Parse intervals
    # -----------------------------------------------------
    interval_pattern = re.compile(
        r'xmin\s*=\s*([0-9.eE+-]+)\s+'
        r'xmax\s*=\s*([0-9.eE+-]+)\s+'
        r'text\s*=\s*"([^"]*)"',
        flags=re.DOTALL
    )

    phonemes = []

    for match in interval_pattern.finditer(
        phone_block
    ):

        start = float(
            match.group(1)
        )

        end = float(
            match.group(2)
        )

        label = (
            match.group(3)
            .strip()
        )

        # Ignore silence
        if label.lower() in SILENCE_LABELS:
            continue

        # Ignore invalid intervals
        if end <= start:
            continue

        phonemes.append(
            {
                "phoneme": label,
                "start": round(
                    start,
                    4
                ),
                "end": round(
                    end,
                    4
                ),
                "duration": round(
                    end - start,
                    4
                ),
            }
        )

    if not phonemes:

        raise ValueError(
            "No valid phoneme intervals were found "
            "in the TextGrid."
        )

    return phonemes


# ---------------------------------------------------------
# Analyze phoneme timing
# ---------------------------------------------------------
def analyze_phoneme_timing(
    phonemes
):
    """
    Calculate timing statistics from aligned phonemes.
    """

    if not phonemes:

        return {
            "phoneme_count": 0,
            "mean_duration": 0.0,
            "median_duration": 0.0,
            "std_duration": 0.0,
            "min_duration": 0.0,
            "max_duration": 0.0,
            "duration_variation": 0.0,
            "timing_consistency_score": 0.0,
        }

    durations = [
        phoneme["duration"]
        for phoneme in phonemes
    ]

    mean_duration = statistics.mean(
        durations
    )

    median_duration = statistics.median(
        durations
    )

    if len(durations) > 1:

        std_duration = statistics.stdev(
            durations
        )

    else:

        std_duration = 0.0

    # Coefficient of variation
    if mean_duration > 0:

        duration_variation = (
            std_duration /
            mean_duration
        )

    else:

        duration_variation = 0.0

    # -----------------------------------------------------
    # Timing consistency score
    #
    # This is a research-oriented normalized timing
    # consistency indicator, NOT a clinical score.
    # -----------------------------------------------------
    timing_consistency = (
        100.0 /
        (
            1.0 +
            duration_variation
        )
    )

    timing_consistency = max(
        0.0,
        min(
            100.0,
            timing_consistency
        )
    )

    return {
        "phoneme_count": len(
            phonemes
        ),

        "mean_duration": round(
            mean_duration,
            4
        ),

        "median_duration": round(
            median_duration,
            4
        ),

        "std_duration": round(
            std_duration,
            4
        ),

        "min_duration": round(
            min(durations),
            4
        ),

        "max_duration": round(
            max(durations),
            4
        ),

        "duration_variation": round(
            duration_variation,
            4
        ),

        "timing_consistency_score": round(
            timing_consistency,
            2
        ),
    }


# ---------------------------------------------------------
# Detect timing irregularities
# ---------------------------------------------------------
def detect_timing_irregularities(
    phonemes
):
    """
    Detect unusually short or long phoneme intervals
    relative to the utterance itself.

    This is an analytical flag, not a clinical diagnosis.
    """

    if len(phonemes) < 2:

        return {
            "irregular_phoneme_count": 0,
            "irregular_phonemes": [],
        }

    durations = [
        phoneme["duration"]
        for phoneme in phonemes
    ]

    mean_duration = statistics.mean(
        durations
    )

    if len(durations) > 1:

        std_duration = statistics.stdev(
            durations
        )

    else:

        std_duration = 0.0

    irregular = []

    # Use a minimum variability floor so that
    # nearly identical durations do not cause
    # unstable thresholds.
    threshold = max(
        std_duration,
        mean_duration * 0.50
    )

    lower_bound = max(
        0.005,
        mean_duration - threshold
    )

    upper_bound = (
        mean_duration +
        threshold
    )

    for phoneme in phonemes:

        duration = phoneme[
            "duration"
        ]

        if (
            duration < lower_bound
            or duration > upper_bound
        ):

            irregular.append(
                {
                    "phoneme":
                        phoneme["phoneme"],

                    "duration":
                        phoneme["duration"],

                    "reason":
                        (
                            "Unusually short or "
                            "long duration"
                        ),
                }
            )

    return {
        "irregular_phoneme_count": len(
            irregular
        ),

        "irregular_phonemes": irregular,
    }


# ---------------------------------------------------------
# Analyze alignment quality
# ---------------------------------------------------------
def analyze_alignment_quality(
    phonemes
):
    """
    Analyze structural quality of the alignment.

    NOTE:
    This is not an acoustic confidence probability.
    It checks the validity and continuity of intervals.
    """

    if not phonemes:

        return {
            "alignment_reliability": 0.0,
            "quality": "Low",
            "uncertainty_flag": True,
            "invalid_intervals": 0,
            "overlapping_intervals": 0,
        }

    invalid_intervals = 0
    overlapping_intervals = 0

    previous_end = None

    for phoneme in phonemes:

        start = phoneme["start"]
        end = phoneme["end"]

        if end <= start:
            invalid_intervals += 1

        if phoneme["duration"] <= 0:
            invalid_intervals += 1

        if (
            previous_end is not None
            and start < previous_end
        ):

            overlapping_intervals += 1

        previous_end = end

    total_checks = len(
        phonemes
    )

    invalid_ratio = (
        invalid_intervals /
        total_checks
    )

    overlap_ratio = (
        overlapping_intervals /
        total_checks
    )

    structural_error = (
        invalid_ratio +
        overlap_ratio
    )

    reliability = (
        100.0 *
        (
            1.0 -
            min(
                1.0,
                structural_error
            )
        )
    )

    reliability = max(
        0.0,
        min(
            100.0,
            reliability
        )
    )

    if reliability >= 90:

        quality = "High"

    elif reliability >= 75:

        quality = "Medium"

    else:

        quality = "Low"

    return {
        "alignment_reliability": round(
            reliability,
            2
        ),

        "quality": quality,

        "uncertainty_flag": (
            reliability < 75
        ),

        "invalid_intervals":
            invalid_intervals,

        "overlapping_intervals":
            overlapping_intervals,
    }


# ---------------------------------------------------------
# Overall TextGrid analysis
# ---------------------------------------------------------
def analyze_textgrid(
    textgrid_path: str
):

    phonemes = parse_textgrid(
        textgrid_path
    )

    timing = analyze_phoneme_timing(
        phonemes
    )

    irregularities = (
        detect_timing_irregularities(
            phonemes
        )
    )

    alignment = (
        analyze_alignment_quality(
            phonemes
        )
    )

    return {
        "phonemes": phonemes,
        "timing": timing,
        "timing_irregularities":
            irregularities,
        "alignment": alignment,
    }