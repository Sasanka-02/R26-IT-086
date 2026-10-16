import librosa
import numpy as np


def extract_speech_features(audio_path: str) -> dict:
    """
    Extract speech features for Component 2.

    This function extracts measurable acoustic features only.
    It does not assign an articulation score.

    The returned feature names must remain consistent with
    the features used during model training.
    """

    # ---------------------------------------------------------
    # Load audio
    # ---------------------------------------------------------
    y, sr = librosa.load(
        audio_path,
        sr=None,
        mono=True
    )

    duration = float(
        librosa.get_duration(
            y=y,
            sr=sr
        )
    )

    # ---------------------------------------------------------
    # RMS / intensity features
    # ---------------------------------------------------------
    rms = librosa.feature.rms(
        y=y
    )[0]

    mean_rms = float(
        np.mean(rms)
    )

    std_rms = float(
        np.std(rms)
    )

    min_rms = float(
        np.min(rms)
    )

    max_rms = float(
        np.max(rms)
    )

    rms_range = (
        max_rms -
        min_rms
    )

    # ---------------------------------------------------------
    # Zero-crossing features
    # ---------------------------------------------------------
    zcr = librosa.feature.zero_crossing_rate(
        y
    )[0]

    mean_zcr = float(
        np.mean(zcr)
    )

    std_zcr = float(
        np.std(zcr)
    )

    # ---------------------------------------------------------
    # Spectral features
    # ---------------------------------------------------------
    spectral_centroid = (
        librosa.feature.spectral_centroid(
            y=y,
            sr=sr
        )[0]
    )

    spectral_bandwidth = (
        librosa.feature.spectral_bandwidth(
            y=y,
            sr=sr
        )[0]
    )

    spectral_rolloff = (
        librosa.feature.spectral_rolloff(
            y=y,
            sr=sr
        )[0]
    )

    mean_spectral_centroid = float(
        np.mean(spectral_centroid)
    )

    std_spectral_centroid = float(
        np.std(spectral_centroid)
    )

    mean_spectral_bandwidth = float(
        np.mean(spectral_bandwidth)
    )

    std_spectral_bandwidth = float(
        np.std(spectral_bandwidth)
    )

    mean_spectral_rolloff = float(
        np.mean(spectral_rolloff)
    )

    std_spectral_rolloff = float(
        np.std(spectral_rolloff)
    )

    # ---------------------------------------------------------
    # Pitch / F0 features
    # ---------------------------------------------------------
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr
    )

    valid_f0 = f0[
        ~np.isnan(f0)
    ]

    if len(valid_f0) > 0:

        mean_f0 = float(
            np.mean(valid_f0)
        )

        std_f0 = float(
            np.std(valid_f0)
        )

        min_f0 = float(
            np.min(valid_f0)
        )

        max_f0 = float(
            np.max(valid_f0)
        )

        f0_range = (
            max_f0 -
            min_f0
        )

    else:

        mean_f0 = 0.0
        std_f0 = 0.0
        min_f0 = 0.0
        max_f0 = 0.0
        f0_range = 0.0

    # ---------------------------------------------------------
    # Voice activity / pause features
    # ---------------------------------------------------------
    silence_threshold = 0.02

    silent_frames = np.sum(
        rms < silence_threshold
    )

    total_frames = len(
        rms
    )

    if total_frames > 0:

        pause_ratio = float(
            silent_frames /
            total_frames
        )

    else:

        pause_ratio = 0.0

    # ---------------------------------------------------------
    # Speech regions
    # ---------------------------------------------------------
    voiced_mask = (
        rms >=
        silence_threshold
    )

    speech_frame_count = int(
        np.sum(
            voiced_mask
        )
    )

    if total_frames > 0:

        speech_ratio = float(
            speech_frame_count /
            total_frames
        )

    else:

        speech_ratio = 0.0

    # Count speech segment starts
    if len(voiced_mask) > 1:

        transitions = np.diff(
            voiced_mask.astype(int)
        )

        speech_start_count = int(
            np.sum(
                transitions == 1
            )
        )

    else:

        speech_start_count = 0

    if (
        len(voiced_mask) > 0
        and voiced_mask[0]
    ):

        speech_start_count += 1

    number_of_speech_segments = (
        speech_start_count
    )

    # ---------------------------------------------------------
    # Speech-rate proxy
    # ---------------------------------------------------------
    #
    # This is a temporal speech-activity indicator.
    # It is NOT an actual words-per-minute articulation rate.
    #
    if duration > 0:

        speech_rate_proxy = (
            speech_ratio /
            duration
        )

    else:

        speech_rate_proxy = 0.0

    # ---------------------------------------------------------
    # MFCC features
    # ---------------------------------------------------------
    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=13
    )

    mfcc_mean = np.mean(
        mfcc,
        axis=1
    )

    mfcc_std = np.std(
        mfcc,
        axis=1
    )

    mfcc_mean_dict = {
        f"mfcc_{index + 1}_mean":
            float(value)

        for index, value
        in enumerate(mfcc_mean)
    }

    mfcc_std_dict = {
        f"mfcc_{index + 1}_std":
            float(value)

        for index, value
        in enumerate(mfcc_std)
    }

    # ---------------------------------------------------------
    # Final feature vector
    # ---------------------------------------------------------
    features = {

        # IMPORTANT:
        # Both names are kept because the training dataset
        # contains both fields. They represent the same
        # measured audio duration.
        "duration": round(
            duration,
            4
        ),

        "duration_seconds": round(
            duration,
            4
        ),

        # Audio properties
        "sample_rate": int(
            sr
        ),

        # -----------------------------------------------------
        # RMS / intensity
        # -----------------------------------------------------
        "mean_rms_energy": round(
            mean_rms,
            6
        ),

        "std_rms_energy": round(
            std_rms,
            6
        ),

        "min_rms_energy": round(
            min_rms,
            6
        ),

        "max_rms_energy": round(
            max_rms,
            6
        ),

        "rms_range": round(
            rms_range,
            6
        ),

        # -----------------------------------------------------
        # Zero crossing
        # -----------------------------------------------------
        "mean_zero_crossing_rate": round(
            mean_zcr,
            6
        ),

        "std_zero_crossing_rate": round(
            std_zcr,
            6
        ),

        # -----------------------------------------------------
        # Spectral
        # -----------------------------------------------------
        "mean_spectral_centroid": round(
            mean_spectral_centroid,
            4
        ),

        "std_spectral_centroid": round(
            std_spectral_centroid,
            4
        ),

        "mean_spectral_bandwidth": round(
            mean_spectral_bandwidth,
            4
        ),

        "std_spectral_bandwidth": round(
            std_spectral_bandwidth,
            4
        ),

        "mean_spectral_rolloff": round(
            mean_spectral_rolloff,
            4
        ),

        "std_spectral_rolloff": round(
            std_spectral_rolloff,
            4
        ),

        # -----------------------------------------------------
        # Fundamental frequency
        # -----------------------------------------------------
        "mean_f0_hz": round(
            mean_f0,
            4
        ),

        "std_f0_hz": round(
            std_f0,
            4
        ),

        "min_f0_hz": round(
            min_f0,
            4
        ),

        "max_f0_hz": round(
            max_f0,
            4
        ),

        "f0_range_hz": round(
            f0_range,
            4
        ),

        # -----------------------------------------------------
        # Pause / speech activity
        # -----------------------------------------------------
        "pause_ratio": round(
            pause_ratio,
            4
        ),

        "speech_ratio": round(
            speech_ratio,
            4
        ),

        "number_of_speech_segments":
            number_of_speech_segments,

        "speech_rate_proxy": round(
            speech_rate_proxy,
            6
        ),

        # -----------------------------------------------------
        # MFCC
        # -----------------------------------------------------
        **mfcc_mean_dict,
        **mfcc_std_dict
    }

    return features