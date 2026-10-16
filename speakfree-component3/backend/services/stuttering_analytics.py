import re
from statistics import mean, stdev


# =========================================================
# Common filler / hesitation words
# =========================================================

FILLER_WORDS = {
    "uh",
    "um",
    "er",
    "ah",
    "eh",
    "hmm",
}


# =========================================================
# Normalize ASR text
# =========================================================

def normalize_text(text: str):
    """
    Convert ASR text into a normalized word sequence.
    """

    if not text:
        return []

    text = text.lower()

    words = re.findall(
        r"\b[a-zA-Z']+\b",
        text
    )

    return words


# =========================================================
# Detect immediate word repetitions
# =========================================================

def detect_word_repetitions(words):
    """
    Detect immediate word repetitions.

    Example:
        "I I I want to go"

    This is an observable fluency indicator.
    It is not a clinical diagnosis.
    """

    repetitions = []

    for index in range(
        1,
        len(words)
    ):

        current = words[index]
        previous = words[index - 1]

        if current == previous:

            repetitions.append(
                {
                    "word": current,
                    "position": index,
                    "type": "immediate_word_repetition",
                }
            )

    return repetitions


# =========================================================
# Detect repeated two-word phrases
# =========================================================

def detect_phrase_repetitions(words):
    """
    Detect repeated adjacent two-word phrases.

    Example:
        "I want I want to go"
    """

    repetitions = []

    if len(words) < 4:
        return repetitions

    for index in range(
        2,
        len(words) - 1
    ):

        previous_pair = (
            words[index - 2],
            words[index - 1],
        )

        current_pair = (
            words[index],
            words[index + 1],
        )

        if previous_pair == current_pair:

            repetitions.append(
                {
                    "phrase":
                        " ".join(
                            current_pair
                        ),

                    "position":
                        index,

                    "type":
                        "phrase_repetition",
                }
            )

    return repetitions


# =========================================================
# Detect fillers / hesitations
# =========================================================

def detect_fillers(words):

    fillers = []

    for index, word in enumerate(words):

        if word in FILLER_WORDS:

            fillers.append(
                {
                    "word": word,
                    "position": index,
                    "type": "filler_or_hesitation",
                }
            )

    return fillers


# =========================================================
# Analyze Whisper segment timing
# =========================================================

def calculate_segment_timing(
    segments
):
    """
    Calculate speech and pause timing from Whisper
    timestamped segments.
    """

    if not segments:

        return {
            "segment_count": 0,
            "mean_segment_duration": 0.0,
            "pause_count": 0,
            "mean_pause_duration": 0.0,
            "pause_duration_variation": 0.0,
            "long_pause_count": 0,
            "long_pauses": [],
        }

    segment_durations = []
    pause_durations = []
    long_pauses = []

    previous_end = None

    for segment in segments:

        start = float(
            segment.get(
                "start",
                0.0
            )
        )

        end = float(
            segment.get(
                "end",
                start
            )
        )

        duration = max(
            0.0,
            end - start
        )

        segment_durations.append(
            duration
        )

        # ---------------------------------------------
        # Detect pause between consecutive segments
        # ---------------------------------------------

        if (
            previous_end is not None
            and start > previous_end
        ):

            pause_duration = (
                start -
                previous_end
            )

            pause_durations.append(
                pause_duration
            )

            # A pause >= 1 second is treated as
            # a long-pause indicator for this prototype.
            if pause_duration >= 1.0:

                long_pauses.append(
                    {
                        "start":
                            round(
                                previous_end,
                                3
                            ),

                        "end":
                            round(
                                start,
                                3
                            ),

                        "duration":
                            round(
                                pause_duration,
                                3
                            ),

                        "type":
                            "long_pause",
                    }
                )

        previous_end = max(
            previous_end or 0.0,
            end
        )

    mean_segment_duration = (
        mean(
            segment_durations
        )
        if segment_durations
        else 0.0
    )

    mean_pause_duration = (
        mean(
            pause_durations
        )
        if pause_durations
        else 0.0
    )

    pause_variation = (
        stdev(
            pause_durations
        )
        if len(pause_durations) > 1
        else 0.0
    )

    return {
        "segment_count":
            len(segment_durations),

        "mean_segment_duration":
            round(
                mean_segment_duration,
                3
            ),

        "pause_count":
            len(pause_durations),

        "mean_pause_duration":
            round(
                mean_pause_duration,
                3
            ),

        "pause_duration_variation":
            round(
                pause_variation,
                3
            ),

        "long_pause_count":
            len(long_pauses),

        "long_pauses":
            long_pauses,
    }


# =========================================================
# Speech-rate analysis
# =========================================================

def calculate_speech_rate(
    words,
    segments
):
    """
    Estimate words per minute from ASR timestamps.

    This is a speech-rate indicator and not a clinical
    fluency measure.
    """

    if not words or not segments:

        return {
            "words_per_minute": 0.0
        }

    start = float(
        segments[0].get(
            "start",
            0.0
        )
    )

    end = float(
        segments[-1].get(
            "end",
            0.0
        )
    )

    duration = end - start

    if duration <= 0:

        return {
            "words_per_minute": 0.0
        }

    words_per_minute = (
        len(words)
        / duration
        * 60.0
    )

    return {
        "words_per_minute":
            round(
                words_per_minute,
                2
            )
    }


# =========================================================
# Fluency indicator scoring
# =========================================================

def calculate_fluency_indicators(
    words,
    repetitions,
    phrase_repetitions,
    fillers,
    timing,
    speech_rate
):
    """
    Combine observable fluency indicators.

    IMPORTANT:
    This is a research prototype heuristic.
    It is NOT a clinically validated stuttering scale.
    """

    word_count = len(
        words
    )

    repetition_count = len(
        repetitions
    )

    phrase_repetition_count = len(
        phrase_repetitions
    )

    filler_count = len(
        fillers
    )

    long_pause_count = timing.get(
        "long_pause_count",
        0
    )

    # ---------------------------------------------
    # Rates
    # ---------------------------------------------

    if word_count > 0:

        repetition_rate = (
            repetition_count /
            word_count
        )

        filler_rate = (
            filler_count /
            word_count
        )

    else:

        repetition_rate = 0.0
        filler_rate = 0.0

    # ---------------------------------------------
    # Penalties
    # ---------------------------------------------

    repetition_penalty = min(
        40.0,
        repetition_rate * 100.0
    )

    phrase_penalty = min(
        20.0,
        phrase_repetition_count * 5.0
    )

    filler_penalty = min(
        15.0,
        filler_rate * 100.0
    )

    pause_penalty = min(
        20.0,
        long_pause_count * 5.0
    )

    # ---------------------------------------------
    # Fluency score
    # ---------------------------------------------

    score = (
        100.0
        - repetition_penalty
        - phrase_penalty
        - filler_penalty
        - pause_penalty
    )

    score = max(
        0.0,
        min(
            100.0,
            score
        )
    )

    # ---------------------------------------------
    # Interpretation
    # ---------------------------------------------

    if score >= 80:

        interpretation = (
            "Generally fluent speech indicators"
        )

    elif score >= 60:

        interpretation = (
            "Some fluency disruption indicators detected"
        )

    elif score >= 40:

        interpretation = (
            "Moderate fluency disruption indicators detected"
        )

    else:

        interpretation = (
            "High fluency disruption indicators detected"
        )

    return {
        "fluency_score":
            round(
                score,
                2
            ),

        "repetition_rate":
            round(
                repetition_rate,
                4
            ),

        "filler_rate":
            round(
                filler_rate,
                4
            ),

        "long_pause_count":
            long_pause_count,

        "words_per_minute":
            speech_rate.get(
                "words_per_minute",
                0.0
            ),

        "interpretation":
            interpretation,
    }


# =========================================================
# Main stuttering / fluency analysis
# =========================================================

def analyze_stuttering(
    recognized_text: str,
    segments: list
):
    """
    Analyze observable fluency/disfluency indicators
    from ASR text and timing.

    This does NOT diagnose stuttering.
    """

    words = normalize_text(
        recognized_text
    )

    repetitions = (
        detect_word_repetitions(
            words
        )
    )

    phrase_repetitions = (
        detect_phrase_repetitions(
            words
        )
    )

    fillers = (
        detect_fillers(
            words
        )
    )

    timing = (
        calculate_segment_timing(
            segments
        )
    )

    speech_rate = (
        calculate_speech_rate(
            words,
            segments
        )
    )

    fluency = (
        calculate_fluency_indicators(
            words,
            repetitions,
            phrase_repetitions,
            fillers,
            timing,
            speech_rate
        )
    )

    total_disfluency_indicators = (
        len(repetitions)
        +
        len(phrase_repetitions)
        +
        len(fillers)
        +
        timing.get(
            "long_pause_count",
            0
        )
    )

    return {

        "analysis_type":
            "fluency_and_stuttering_indicators",

        "word_count":
            len(words),

        "word_repetitions":
            repetitions,

        "phrase_repetitions":
            phrase_repetitions,

        "fillers_and_hesitations":
            fillers,

        "timing":
            timing,

        "speech_rate":
            speech_rate,

        "fluency":
            fluency,

        "total_observable_disfluency_indicators":
            total_disfluency_indicators,

        "clinical_note":
            (
                "These are observable speech-fluency "
                "indicators for research purposes. "
                "They are not a clinical diagnosis "
                "of stuttering."
            ),
    }