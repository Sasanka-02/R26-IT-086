"""
Treatment-Response Voice Biomarker Comparison Engine.

Compares a patient's post-treatment response metrics (as would be
produced by Component 1's feature extraction pipeline) against a
normative profile for the same task, producing a delta vector — the
objective progress measure described in the proposal.
"""

import numpy as np

NORMATIVE_PROFILES: dict[str, dict[str, float]] = {
    "picture_description": {
        "words_per_minute": 130.0,
        "zero_crossing_rate_mean": 0.05,
        "energy_mean": 0.05,
        "tempo_bpm": 100.0,
    },
    "video_description": {
        "words_per_minute": 125.0,
        "zero_crossing_rate_mean": 0.05,
        "energy_mean": 0.05,
        "tempo_bpm": 100.0,
    },
    "conversation": {
        "words_per_minute": 140.0,
        "zero_crossing_rate_mean": 0.045,
        "energy_mean": 0.055,
        "tempo_bpm": 105.0,
    },
}


def compute_delta_vector(task_type: str, patient_metrics: dict) -> dict:
    """
    patient_metrics is expected to be the fluency_metrics + acoustic_features
    dict produced by Component 1's feature_extractor for this task — no
    re-extraction here, just comparison against the norm.
    """
    norm = NORMATIVE_PROFILES.get(task_type, NORMATIVE_PROFILES["conversation"])

    delta = {}
    for key, norm_value in norm.items():
        patient_value = patient_metrics.get(key)
        if patient_value is None:
            continue
        delta[key] = {
            "patient": patient_value,
            "normative": norm_value,
            "delta": patient_value - norm_value,
            "percent_deviation": (
                round(100 * (patient_value - norm_value) / norm_value, 1)
                if norm_value
                else None
            ),
        }
    return delta


def overall_progress_score(delta_vector: dict) -> float:
    """
    Single 0-100 'closeness to normative speech' score — smaller absolute
    percent deviation across dimensions => higher score.
    """
    deviations = [
        abs(v["percent_deviation"])
        for v in delta_vector.values()
        if v.get("percent_deviation") is not None
    ]
    if not deviations:
        return 0.0
    avg_deviation = float(np.mean(deviations))
    return round(max(0.0, 100.0 - avg_deviation), 1)
