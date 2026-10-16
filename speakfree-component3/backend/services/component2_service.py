from pathlib import Path
import os
import subprocess
import tempfile

import joblib
import librosa
import numpy as np
import whisper


from services.feature_extraction import (
    extract_speech_features
)

from services.textgrid_analysis import (
    analyze_textgrid
)

from services.articulation_analytics import (
    analyze_articulation
)

from services.stuttering_analytics import (
    analyze_stuttering
)


# =========================================================
# Configuration
# =========================================================

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

MODEL_PATH = (
    BACKEND_DIR
    / "models"
    / "component2_final_model.joblib"
)

MFA_EXECUTABLE = Path(
    os.environ.get(
        "MFA_EXECUTABLE",
        r"C:\Users\randi\miniforge3\envs\aligner\Scripts\mfa.exe"
    )
)

MFA_ACOUSTIC_MODEL = (
    "english_us_arpa"
)

MFA_DICTIONARY = (
    "english_us_arpa"
)


# =========================================================
# Cached models
# =========================================================

_whisper_model = None
_component2_model = None


# =========================================================
# Whisper model
# =========================================================

def get_whisper_model():

    global _whisper_model

    if _whisper_model is None:

        print(
            "Loading Whisper model..."
        )

        _whisper_model = (
            whisper.load_model(
                "tiny.en"
            )
        )

    return _whisper_model


# =========================================================
# Component 2 trained model
# =========================================================

def get_component2_model():

    global _component2_model

    if _component2_model is None:

        if not MODEL_PATH.exists():

            raise FileNotFoundError(
                "Component 2 trained model was not found.\n"
                f"Expected:\n{MODEL_PATH}\n\n"
                "Run:\n"
                "training\\train_final_model.py"
            )

        print(
            "Loading Component 2 model..."
        )

        _component2_model = joblib.load(
            MODEL_PATH
        )

    return _component2_model


# =========================================================
# Whisper transcription
# =========================================================

def transcribe_audio(
    audio_path: str
):
    """
    Transcribe audio using Whisper.

    The returned confidence values are ASR-quality
    indicators and are not clinical probabilities.

    Whisper segments are returned because the
    stuttering/fluency module uses their timestamps.
    """

    model = get_whisper_model()

    # Load the audio with librosa instead of letting Whisper shell out to
    # ffmpeg (which is not installed on every dev machine and fails with
    # "[WinError 2] The system cannot find the file specified"). Whisper
    # expects 16 kHz mono float32.
    audio, _ = librosa.load(
        audio_path,
        sr=16000,
        mono=True
    )

    result = model.transcribe(
        audio.astype(np.float32),
        language="en",
        fp16=False
    )

    recognized_text = (
        result.get(
            "text",
            ""
        )
        .strip()
    )

    segments = (
        result.get(
            "segments",
            []
        )
    )

    # -----------------------------------------------------
    # No segments
    # -----------------------------------------------------

    if not segments:

        return {
            "recognized_text":
                recognized_text,

            "word_count":
                len(
                    recognized_text.split()
                ),

            "average_log_probability":
                -2.0,

            "no_speech_probability":
                1.0,

            "asr_confidence_score":
                0.0,

            "segments":
                []
        }

    # -----------------------------------------------------
    # Segment statistics
    # -----------------------------------------------------

    log_probabilities = [
        float(
            segment.get(
                "avg_logprob",
                -2.0
            )
        )
        for segment in segments
    ]

    no_speech_values = [
        float(
            segment.get(
                "no_speech_prob",
                1.0
            )
        )
        for segment in segments
    ]

    average_log_probability = float(
        np.mean(
            log_probabilities
        )
    )

    no_speech_probability = float(
        np.mean(
            no_speech_values
        )
    )

    word_count = len(
        recognized_text.split()
    )

    # -----------------------------------------------------
    # ASR confidence indicator
    # -----------------------------------------------------

    confidence_from_logprob = (
        (
            average_log_probability
            + 1.5
        )
        / 1.5
        * 100.0
    )

    confidence_from_logprob = max(
        0.0,
        min(
            100.0,
            confidence_from_logprob
        )
    )

    confidence = (
        confidence_from_logprob
        *
        (
            1.0
            -
            no_speech_probability
        )
    )

    confidence = max(
        0.0,
        min(
            100.0,
            confidence
        )
    )

    return {
        "recognized_text":
            recognized_text,

        "word_count":
            word_count,

        "average_log_probability":
            round(
                average_log_probability,
                4
            ),

        "no_speech_probability":
            round(
                no_speech_probability,
                4
            ),

        "asr_confidence_score":
            round(
                confidence,
                2
            ),

        "segments":
            segments
    }


# =========================================================
# Acoustic feature extraction
# =========================================================

def extract_inference_features(
    audio_path: str
):
    """
    Extract the same acoustic feature vector used
    by the trained Component 2 model.
    """

    return extract_speech_features(
        audio_path
    )


# =========================================================
# ML prediction
# =========================================================

def predict_dysarthria(
    features: dict
):
    """
    Predict healthy/dysarthria using the trained model.
    """

    model_bundle = (
        get_component2_model()
    )

    pipeline = (
        model_bundle[
            "pipeline"
        ]
    )

    feature_columns = (
        model_bundle[
            "feature_columns"
        ]
    )

    # -----------------------------------------------------
    # Check feature compatibility
    # -----------------------------------------------------

    missing = [
        feature
        for feature in feature_columns
        if feature not in features
    ]

    if missing:

        raise ValueError(
            "Missing inference features:\n"
            +
            ", ".join(
                missing
            )
        )

    # -----------------------------------------------------
    # Build feature vector in training order
    # -----------------------------------------------------

    X = np.array(
        [
            [
                features[
                    feature
                ]
                for feature in feature_columns
            ]
        ],
        dtype=float
    )

    probabilities = (
        pipeline
        .predict_proba(
            X
        )[0]
    )

    classes = list(
        pipeline
        .named_steps[
            "classifier"
        ]
        .classes_
    )

    probability_map = {
        str(label):
            float(probability)

        for label, probability
        in zip(
            classes,
            probabilities
        )
    }

    healthy_probability = (
        probability_map.get(
            "0",
            0.0
        )
    )

    dysarthria_probability = (
        probability_map.get(
            "1",
            0.0
        )
    )

    predicted_class = (
        pipeline.predict(
            X
        )[0]
    )

    # -----------------------------------------------------
    # Risk level
    # -----------------------------------------------------

    if dysarthria_probability >= 0.70:

        risk_level = "high"

    elif dysarthria_probability >= 0.40:

        risk_level = "moderate"

    else:

        risk_level = "low"

    return {
        "predicted_class":
            (
                "dysarthria"
                if int(
                    predicted_class
                ) == 1
                else "healthy"
            ),

        "healthy_probability":
            round(
                healthy_probability,
                4
            ),

        "dysarthria_probability":
            round(
                dysarthria_probability,
                4
            ),

        "dysarthria_risk_score":
            round(
                dysarthria_probability
                * 100.0,
                2
            ),

        "risk_level":
            risk_level
    }


# =========================================================
# MFA alignment
# =========================================================

def run_mfa_alignment(
    audio_path: str,
    transcript: str
):
    """
    Perform MFA forced alignment using a supplied
    reference transcript.

    The reference transcript is expected to be the
    word/sentence that the speaker was instructed to say.
    """

    transcript = (
        transcript
        .strip()
    )

    if not transcript:

        return {
            "success":
                False,

            "reason":
                "No reference transcript was provided."
        }

    if not MFA_EXECUTABLE.exists():

        return {
            "success":
                False,

            "reason":
                "MFA executable not found.",

            "details":
                str(
                    MFA_EXECUTABLE
                )
        }

    # -----------------------------------------------------
    # Temporary MFA corpus
    # -----------------------------------------------------

    with tempfile.TemporaryDirectory(
        prefix="component2_mfa_"
    ) as temp_dir:

        temp_path = Path(
            temp_dir
        )

        corpus_path = (
            temp_path
            / "corpus"
        )

        output_path = (
            temp_path
            / "output"
        )

        corpus_path.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path.mkdir(
            parents=True,
            exist_ok=True
        )

        audio_destination = (
            corpus_path
            / "sample.wav"
        )

        transcript_destination = (
            corpus_path
            / "sample.txt"
        )

        # -------------------------------------------------
        # Convert audio to WAV
        # -------------------------------------------------

        try:

            y, sr = librosa.load(
                audio_path,
                sr=None,
                mono=True
            )

            import soundfile as sf

            sf.write(
                str(
                    audio_destination
                ),
                y,
                sr
            )

        except Exception as error:

            return {
                "success":
                    False,

                "reason":
                    "Could not prepare audio for MFA.",

                "details":
                    str(error)
            }

        # -------------------------------------------------
        # Write exact reference transcript
        # -------------------------------------------------

        transcript_destination.write_text(
            transcript,
            encoding="utf-8"
        )

        # -------------------------------------------------
        # MFA validation
        # -------------------------------------------------

        validate_command = [
            str(MFA_EXECUTABLE),
            "validate",
            str(corpus_path),
            MFA_DICTIONARY
        ]

        try:

            validation = subprocess.run(
                validate_command,
                capture_output=True,
                text=True,
                timeout=300
            )

        except subprocess.TimeoutExpired:

            return {
                "success":
                    False,

                "reason":
                    "MFA validation timed out."
            }

        except Exception as error:

            return {
                "success":
                    False,

                "reason":
                    "Could not start MFA validation.",

                "details":
                    str(error)
            }

        if validation.returncode != 0:

            return {
                "success":
                    False,

                "reason":
                    "MFA validation failed.",

                "details":
                    (
                        validation.stderr[-3000:]
                        if validation.stderr
                        else validation.stdout[-3000:]
                    )
            }

        # -------------------------------------------------
        # MFA alignment
        # -------------------------------------------------

        align_command = [
            str(MFA_EXECUTABLE),
            "align",
            str(corpus_path),
            MFA_DICTIONARY,
            MFA_ACOUSTIC_MODEL,
            str(output_path)
        ]

        try:

            alignment = subprocess.run(
                align_command,
                capture_output=True,
                text=True,
                timeout=300
            )

        except subprocess.TimeoutExpired:

            return {
                "success":
                    False,

                "reason":
                    "MFA alignment timed out."
            }

        except Exception as error:

            return {
                "success":
                    False,

                "reason":
                    "Could not start MFA alignment.",

                "details":
                    str(error)
            }

        if alignment.returncode != 0:

            return {
                "success":
                    False,

                "reason":
                    "MFA alignment failed.",

                "details":
                    (
                        alignment.stderr[-3000:]
                        if alignment.stderr
                        else alignment.stdout[-3000:]
                    )
            }

        # -------------------------------------------------
        # TextGrid
        # -------------------------------------------------

        textgrid_path = (
            output_path
            / "sample.TextGrid"
        )

        if not textgrid_path.exists():

            return {
                "success":
                    False,

                "reason":
                    (
                        "MFA completed but no "
                        "TextGrid was produced."
                    )
            }

        # -------------------------------------------------
        # TextGrid analysis
        # -------------------------------------------------

        try:

            analysis = (
                analyze_textgrid(
                    str(
                        textgrid_path
                    )
                )
            )

        except Exception as error:

            return {
                "success":
                    False,

                "reason":
                    "TextGrid analysis failed.",

                "details":
                    str(error)
            }

        return {
            "success":
                True,

            "analysis":
                analysis
        }


# =========================================================
# Main Component 2 analysis
# =========================================================

def analyze_articulation(
    audio_path: str,
    reference_text: str = ""
):
    """
    Complete Component 2 pipeline.

    Includes:

    1. Whisper transcription
    2. Acoustic feature extraction
    3. Dysarthria ML prediction
    4. Stuttering/fluency indicators
    5. Optional reference-text MFA alignment
    6. Phoneme timing analysis
    7. Articulation analytics
    8. Component 3-ready output
    """

    reference_text = (
        reference_text
        .strip()
    )

    # =====================================================
    # 1. Whisper
    # =====================================================

    asr_result = (
        transcribe_audio(
            audio_path
        )
    )

    # =====================================================
    # 2. Stuttering / fluency analysis
    # =====================================================

    stuttering_result = (
        analyze_stuttering(
            recognized_text=
                asr_result[
                    "recognized_text"
                ],

            segments=
                asr_result.get(
                    "segments",
                    []
                )
        )
    )

    # =====================================================
    # 3. Acoustic features
    # =====================================================

    acoustic_features = (
        extract_inference_features(
            audio_path
        )
    )

    # =====================================================
    # 4. Dysarthria ML model
    # =====================================================

    ml_result = (
        predict_dysarthria(
            acoustic_features
        )
    )

    # =====================================================
    # 5. MFA alignment
    # =====================================================
    #
    # MFA is performed only when the user provides
    # the expected/reference text.
    #
    # This avoids trying to force-align unreliable
    # spontaneous Whisper transcripts.
    # =====================================================

    if reference_text:

        alignment_mode = (
            "reference_text_alignment"
        )

        mfa_result = (
            run_mfa_alignment(
                audio_path=
                    audio_path,

                transcript=
                    reference_text
            )
        )

    else:

        alignment_mode = (
            "spontaneous_asr_assisted"
        )

        mfa_result = {
            "success":
                False,

            "reason":
                (
                    "No reference text supplied. "
                    "Phoneme-level forced alignment "
                    "was not requested."
                )
        }

    # =====================================================
    # 6. Default alignment response
    # =====================================================

    phoneme_analysis = None

    timing_result = {}

    articulation_result = None

    alignment_result = {

        "alignment_available":
            False,

        "reliability":
            None,

        "quality":
            "Unavailable",

        "uncertainty_flag":
            True,

        "reason":
            mfa_result.get(
                "reason",
                "Alignment unavailable."
            )
    }

    # =====================================================
    # 7. Process successful MFA alignment
    # =====================================================

    if mfa_result.get(
        "success",
        False
    ):

        phoneme_analysis = (
            mfa_result[
                "analysis"
            ]
        )

        timing_result = (
            phoneme_analysis[
                "timing"
            ]
        )

        alignment_data = (
            phoneme_analysis[
                "alignment"
            ]
        )

        alignment_result = {

            "alignment_available":
                True,

            "reliability":
                alignment_data.get(
                    "alignment_reliability"
                ),

            "quality":
                alignment_data.get(
                    "quality"
                ),

            "uncertainty_flag":
                alignment_data.get(
                    "uncertainty_flag",
                    False
                ),

            "reason":
                None
        }

        # =================================================
        # 8. Articulation analytics
        # =================================================

        articulation_result = (
            analyze_articulation(
                phonemes=
                    phoneme_analysis[
                        "phonemes"
                    ],

                dysarthria_probability=
                    ml_result[
                        "dysarthria_probability"
                    ]
            )
        )

    # =====================================================
    # 9. Component 3-ready output
    # =====================================================

    component3_ready_output = {

        # ---------------------------------------------
        # Dysarthria
        # ---------------------------------------------

        "dysarthria_risk_score":
            ml_result[
                "dysarthria_risk_score"
            ],

        "dysarthria_probability":
            ml_result[
                "dysarthria_probability"
            ],

        "risk_level":
            ml_result[
                "risk_level"
            ],

        # ---------------------------------------------
        # Stuttering / fluency
        # ---------------------------------------------

        "fluency_score":
            stuttering_result[
                "fluency"
            ][
                "fluency_score"
            ],

        "word_repetition_count":
            len(
                stuttering_result[
                    "word_repetitions"
                ]
            ),

        "phrase_repetition_count":
            len(
                stuttering_result[
                    "phrase_repetitions"
                ]
            ),

        "filler_count":
            len(
                stuttering_result[
                    "fillers_and_hesitations"
                ]
            ),

        "speech_rate_wpm":
            stuttering_result[
                "speech_rate"
            ][
                "words_per_minute"
            ],

        "long_pause_count":
            stuttering_result[
                "timing"
            ].get(
                "long_pause_count",
                0
            ),

        # ---------------------------------------------
        # Phoneme timing
        # ---------------------------------------------

        "timing_consistency":
            (
                timing_result.get(
                    "timing_consistency_score"
                )
                if timing_result
                else None
            ),

        "duration_variation":
            (
                timing_result.get(
                    "duration_variation"
                )
                if timing_result
                else None
            ),

        "phoneme_count":
            (
                timing_result.get(
                    "phoneme_count",
                    0
                )
                if timing_result
                else 0
            ),

        # ---------------------------------------------
        # Alignment
        # ---------------------------------------------

        "alignment_reliability":
            alignment_result[
                "reliability"
            ],

        "alignment_uncertain":
            alignment_result[
                "uncertainty_flag"
            ]
    }

    # =====================================================
    # 10. Final Component 2 response
    # =====================================================

    output = {

        "component":
            (
                "Component 2 - "
                "Alignment and Articulation Analytics"
            ),

        "analysis_mode":
            alignment_mode,

        "alignment_input":
            {
                "mode":
                    alignment_mode,

                "reference_text":
                    (
                        reference_text
                        if reference_text
                        else None
                    ),

                "mfa_used":
                    bool(
                        reference_text
                        and
                        mfa_result.get(
                            "success",
                            False
                        )
                    )
            },

        "received_audio_file":
            os.path.basename(
                audio_path
            ),

        # ---------------------------------------------
        # ASR
        # ---------------------------------------------

        "recognized_text":
            asr_result[
                "recognized_text"
            ],

        "asr_analysis":
            asr_result,

        # ---------------------------------------------
        # Dysarthria ML
        # ---------------------------------------------

        "ml_prediction":
            ml_result,

        # ---------------------------------------------
        # Stuttering / fluency
        # ---------------------------------------------

        "stuttering_analysis":
            stuttering_result,

        # ---------------------------------------------
        # Alignment
        # ---------------------------------------------

        "alignment":
            alignment_result,

        # ---------------------------------------------
        # Phoneme analysis
        # ---------------------------------------------

        "phoneme_analysis":
            phoneme_analysis,

        # ---------------------------------------------
        # Timing
        # ---------------------------------------------

        "timing_analysis":
            timing_result,

        # ---------------------------------------------
        # Articulation
        # ---------------------------------------------

        "articulation_analysis":
            articulation_result,

        # ---------------------------------------------
        # Component 3
        # ---------------------------------------------

        "component3_ready_output":
            component3_ready_output,

        # ---------------------------------------------
        # Research limitation
        # ---------------------------------------------

        "clinical_note":
            (
                "This system is a research screening "
                "prototype. Dysarthria probability is "
                "estimated using a supervised model, "
                "while fluency outputs represent "
                "observable stuttering-related "
                "indicators. These outputs are not "
                "clinical diagnoses."
            )
    }

    return output