"""
Shared constants and the Component 3 feature contract.

IMPORTANT
---------
`FEATURE_ORDER` is the single source of truth for the internal Component 3
feature vector. It is imported by:

    - component3/feature_adapter.py   (inference-time adaptation of C2 output)
    - Training/component3/*.py        (dataset generation + model training)

If you change this list you MUST retrain the models
(`python Training/component3/train_all.py` from the backend directory).
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

MODEL_VERSION = "component3-baseline-v1"

# Where trained model bundles live (created by the training scripts).
BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_DIR / "Models" / "component3"

DISORDER_MODEL_PATH = MODEL_DIR / "disorder_classifier.joblib"
SEVERITY_MODEL_PATH = MODEL_DIR / "severity_estimator.joblib"
STUTTER_MODEL_PATH = MODEL_DIR / "stuttering_multilabel.joblib"
DYSARTHRIA_REAL_MODEL_PATH = MODEL_DIR / "dysarthria_real_torgo.joblib"
MODEL_CARD_PATH = MODEL_DIR / "model_card.json"


# ---------------------------------------------------------------------------
# Label spaces
# ---------------------------------------------------------------------------

DISORDER_CLASSES = ["normal", "stuttering", "dysarthria", "articulation"]

SEVERITY_LEVELS = [1, 2, 3, 4]

SEVERITY_LABELS = {
    1: "Normal",
    2: "Mild",
    3: "Moderate",
    4: "Severe",
}

# Multi-label stuttering event heads.
STUTTER_EVENTS = ["repetition", "prolongation", "block"]


# ---------------------------------------------------------------------------
# Internal feature vector contract (derived ONLY from Component 2 output)
# ---------------------------------------------------------------------------

FEATURE_ORDER = [
    # ---- Component 2 supervised dysarthria model outputs --------------------
    "dysarthria_probability",          # 0..1   (C2 ml_prediction)
    "dysarthria_risk_score",           # 0..100 (C2 ml_prediction)
    "risk_level_ordinal",              # 0/1/2  (low/moderate/high)
    # ---- Component 2 fluency / stuttering indicators -----------------------
    "fluency_score",                   # 0..100
    "word_repetition_count",           # int
    "phrase_repetition_count",         # int
    "filler_count",                    # int
    "speech_rate_wpm",                 # float
    "long_pause_count",                # int
    "total_disfluency_indicators",     # int
    "repetition_rate",                 # 0..1
    "filler_rate",                     # 0..1
    # ---- Component 2 phoneme-timing / articulation analytics --------------
    "timing_consistency",              # 0..100  (imputed if MFA absent)
    "duration_variation",              # >=0     (imputed if MFA absent)
    "phoneme_count",                   # int
    "alignment_reliability",           # 0..100  (imputed if MFA absent)
    "alignment_uncertain",             # 0/1
    "overall_articulation_indicator",  # 0..100  (imputed if MFA absent)
    "phoneme_consistency",             # 0..100  (imputed if MFA absent)
    "acoustic_model_component",        # 0..100  (imputed if MFA absent)
]

# Values used when a Component 2 field is missing/None (e.g. no MFA alignment
# was performed because no reference text was supplied). These are neutral
# placeholders; the trained pipelines also carry a SimpleImputer.
FEATURE_DEFAULTS = {
    "dysarthria_probability": 0.0,
    "dysarthria_risk_score": 0.0,
    "risk_level_ordinal": 0.0,
    "fluency_score": 100.0,
    "word_repetition_count": 0.0,
    "phrase_repetition_count": 0.0,
    "filler_count": 0.0,
    "speech_rate_wpm": 120.0,
    "long_pause_count": 0.0,
    "total_disfluency_indicators": 0.0,
    "repetition_rate": 0.0,
    "filler_rate": 0.0,
    "timing_consistency": 75.0,
    "duration_variation": 0.35,
    "phoneme_count": 0.0,
    "alignment_reliability": 50.0,
    "alignment_uncertain": 1.0,
    "overall_articulation_indicator": 75.0,
    "phoneme_consistency": 75.0,
    "acoustic_model_component": 75.0,
}

RISK_LEVEL_ORDINAL = {"low": 0, "moderate": 1, "medium": 1, "high": 2}


def severity_label(level: int) -> str:
    return SEVERITY_LABELS.get(int(level), "Unknown")
