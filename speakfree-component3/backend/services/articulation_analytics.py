from statistics import mean, median, stdev


SILENCE_LABELS = {
    "",
    "sil",
    "sp",
    "spn",
    "silence",
}


def calculate_timing_metrics(phonemes):
    """
    Calculate timing and duration metrics from
    MFA phoneme intervals.
    """

    spoken = [
        p for p in phonemes
        if p["phoneme"].strip().lower()
        not in SILENCE_LABELS
    ]

    if not spoken:
        return {
            "phoneme_count": 0,
            "mean_phoneme_duration": 0.0,
            "median_phoneme_duration": 0.0,
            "duration_std": 0.0,
            "duration_variation": 0.0,
            "timing_consistency_score": 0.0,
        }

    durations = [
        p["duration"]
        for p in spoken
        if p["duration"] > 0
    ]

    if not durations:
        return {
            "phoneme_count": 0,
            "mean_phoneme_duration": 0.0,
            "median_phoneme_duration": 0.0,
            "duration_std": 0.0,
            "duration_variation": 0.0,
            "timing_consistency_score": 0.0,
        }

    mean_duration = mean(durations)

    median_duration = median(durations)

    duration_std = (
        stdev(durations)
        if len(durations) > 1
        else 0.0
    )

    # Coefficient of variation
    duration_variation = (
        duration_std / mean_duration
        if mean_duration > 0
        else 0.0
    )

    # Normalized consistency indicator.
    timing_consistency = (
        100.0 / (1.0 + duration_variation)
    )

    timing_consistency = max(
        0.0,
        min(
            100.0,
            timing_consistency
        )
    )

    return {
        "phoneme_count": len(spoken),

        "mean_phoneme_duration": round(
            mean_duration,
            4
        ),

        "median_phoneme_duration": round(
            median_duration,
            4
        ),

        "duration_std": round(
            duration_std,
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


def detect_timing_irregularities(phonemes):
    """
    Detect unusually long or short phoneme durations
    relative to the same utterance.

    This is an analytical indicator, not a diagnosis.
    """

    spoken = [
        p for p in phonemes
        if p["phoneme"].strip().lower()
        not in SILENCE_LABELS
    ]

    if len(spoken) < 2:
        return {
            "irregular_count": 0,
            "irregular_phonemes": [],
        }

    durations = [
        p["duration"]
        for p in spoken
        if p["duration"] > 0
    ]

    if len(durations) < 2:
        return {
            "irregular_count": 0,
            "irregular_phonemes": [],
        }

    mean_duration = mean(durations)

    std_duration = stdev(durations)

    # Define an observation threshold.
    lower = max(
        0.01,
        mean_duration - std_duration
    )

    upper = (
        mean_duration + std_duration
    )

    irregular = []

    for phoneme in spoken:

        duration = phoneme["duration"]

        if (
            duration < lower
            or duration > upper
        ):
            irregular.append(
                {
                    "phoneme": phoneme["phoneme"],
                    "start": phoneme["start"],
                    "end": phoneme["end"],
                    "duration": duration,
                    "reason": (
                        "Unusually short or long "
                        "relative to this utterance"
                    ),
                }
            )

    return {
        "irregular_count": len(irregular),
        "irregular_phonemes": irregular,
    }


def calculate_articulation_subscores(
    timing_metrics,
    irregularities,
    dysarthria_probability
):
    """
    Produce interpretable component subscores.

    These are analytical indicators for the prototype.
    They are not clinical diagnostic scores.
    """

    timing_score = (
        timing_metrics[
            "timing_consistency_score"
        ]
    )

    phoneme_count = (
        timing_metrics[
            "phoneme_count"
        ]
    )

    if phoneme_count > 0:

        irregular_ratio = (
            irregularities["irregular_count"]
            / phoneme_count
        )

    else:

        irregular_ratio = 1.0

    irregularity_score = (
        100.0 *
        (1.0 - min(
            1.0,
            irregular_ratio
        ))
    )

    model_score = (
        100.0 *
        (
            1.0 -
            dysarthria_probability
        )
    )

    # Weighted analytical articulation indicator.
    #
    # Timing and phoneme consistency are emphasized
    # over the ML probability.
    overall_score = (
        0.40 * timing_score
        + 0.30 * irregularity_score
        + 0.30 * model_score
    )

    overall_score = max(
        0.0,
        min(
            100.0,
            overall_score
        )
    )

    if overall_score >= 80:
        interpretation = "Good articulation consistency"

    elif overall_score >= 60:
        interpretation = "Moderate articulation consistency"

    elif overall_score >= 40:
        interpretation = "Reduced articulation consistency"

    else:
        interpretation = "Potential articulation difficulty"

    return {
        "timing_consistency": round(
            timing_score,
            2
        ),

        "phoneme_consistency": round(
            irregularity_score,
            2
        ),

        "acoustic_model_component": round(
            model_score,
            2
        ),

        "overall_articulation_indicator": round(
            overall_score,
            2
        ),

        "interpretation": interpretation,
    }


def generate_findings(
    timing_metrics,
    irregularities,
    dysarthria_probability
):
    """
    Generate plain-language analytical findings.
    """

    findings = []

    if timing_metrics[
        "duration_variation"
    ] > 0.75:

        findings.append(
            "High phoneme-duration variability detected"
        )

    elif timing_metrics[
        "duration_variation"
    ] > 0.40:

        findings.append(
            "Moderate phoneme-duration variability detected"
        )

    if irregularities[
        "irregular_count"
    ] > 0:

        findings.append(
            f"{irregularities['irregular_count']} "
            "phoneme timing irregularities detected"
        )

    if dysarthria_probability >= 0.70:

        findings.append(
            "The acoustic model indicates a high "
            "dysarthria-risk probability"
        )

    elif dysarthria_probability >= 0.40:

        findings.append(
            "The acoustic model indicates a moderate "
            "dysarthria-risk probability"
        )

    else:

        findings.append(
            "The acoustic model indicates a lower "
            "dysarthria-risk probability"
        )

    if not findings:

        findings.append(
            "No major timing irregularity detected"
        )

    return findings


def analyze_articulation(
    phonemes,
    dysarthria_probability
):
    """
    Main articulation analytics function.
    """

    timing = calculate_timing_metrics(
        phonemes
    )

    irregularities = (
        detect_timing_irregularities(
            phonemes
        )
    )

    subscores = calculate_articulation_subscores(
        timing,
        irregularities,
        dysarthria_probability
    )

    findings = generate_findings(
        timing,
        irregularities,
        dysarthria_probability
    )

    return {
        "timing": timing,
        "irregularities": irregularities,
        "subscores": subscores,
        "findings": findings,
    }