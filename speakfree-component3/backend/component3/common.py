"""
Shared constants and the Component 3 feature contract.

IMPORTANT
---------
`FEATURE_ORDER` is the single source of truth for the internal Component 3 feature vector.
It is imported by:

    - component3/feature_adapter.py   (inference-time adaptation of the C2 hand-off)
    - training/*.py                   (dataset generation + model training)

If you change this list you MUST retrain the models (`python training/train_all.py`).

v2 (integrated platform): the vector is built from the Component 2 hand-off
(`component3_input`, schema 4.0), which carries Component 2's articulation analytics, the
Component 1 session biomarkers and the TORGO acoustic windows extracted by Component 1.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

MODEL_VERSION = "component3-integrated-v2"

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BACKEND_DIR / "models"

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

SEVERITY_LABELS = {1: "Normal", 2: "Mild", 3: "Moderate", 4: "Severe"}

# Multi-label stuttering event heads.
STUTTER_EVENTS = ["repetition", "prolongation", "block"]


# ---------------------------------------------------------------------------
# Internal feature vector contract (v2)
# ---------------------------------------------------------------------------

FEATURE_ORDER = [
    # ---- Component 2: articulation analytics (C2 novelty) ------------------
    "articulation_score",          # 0..100  A_session (C2-Eq.5)
    "clear_word_ratio",            # 0..1    pooled CWR
    "kept_token_confidence",       # 0..1    pooled C over non-filler tokens
    # ---- Component 1: ASR-confidence biomarker + session scores -----------
    "asr_confidence",              # 0..100  pooled C_overall (C1 Eq.3)
    "dysfluency_ratio",            # 0..1    words with C_word < 0.60 (C1 Eq.2)
    "fluency_score",               # 0..100
    "pronunciation_score",         # 0..100
    "speech_rate_wpm",             # words per minute
    "articulation_rate_sps",       # syllables per second of speech
    "pause_rate_per_min",          # pauses >= 250 ms per minute
    "longest_pause_sec",           # seconds
    # ---- Component 2: fluency events from word timings --------------------
    "filler_rate",                 # 0..1    fillers / words
    "repetition_rate",             # 0..1    (word + phrase repetitions) / content words
    "prolongation_rate",           # 0..1    prolonged words / content words
    "long_pauses_per_min",         # pauses >= 1 s per minute of speech
    # ---- Component 1: sound-level findings ---------------------------------
    "flagged_sound_count",         # sounds with status warning/flag
    # ---- Component 3 stage 1: real-data acoustic model (TORGO) -------------
    "dysarthria_probability",      # 0..1    mean P(dysarthria) over acoustic windows
]

# Neutral values used when a field is missing (documented imputation).
FEATURE_DEFAULTS = {
    "articulation_score": 85.0,
    "clear_word_ratio": 0.92,
    "kept_token_confidence": 0.85,
    "asr_confidence": 85.0,
    "dysfluency_ratio": 0.06,
    "fluency_score": 85.0,
    "pronunciation_score": 85.0,
    "speech_rate_wpm": 120.0,
    "articulation_rate_sps": 4.0,
    "pause_rate_per_min": 10.0,
    "longest_pause_sec": 1.0,
    "filler_rate": 0.02,
    "repetition_rate": 0.01,
    "prolongation_rate": 0.01,
    "long_pauses_per_min": 1.0,
    "flagged_sound_count": 0.0,
    "dysarthria_probability": 0.3,
}

FEATURE_LABELS = {
    "articulation_score": "C2 articulation score",
    "clear_word_ratio": "C2 clear-word ratio",
    "kept_token_confidence": "C2 kept-token confidence",
    "asr_confidence": "C1 ASR confidence (Eq.3)",
    "dysfluency_ratio": "C1 dysfluency ratio",
    "fluency_score": "C1 fluency score",
    "pronunciation_score": "C1 pronunciation score",
    "speech_rate_wpm": "Speech rate (wpm)",
    "articulation_rate_sps": "Articulation rate (syll/s)",
    "pause_rate_per_min": "Pause rate (/min)",
    "longest_pause_sec": "Longest pause (s)",
    "filler_rate": "Filler rate",
    "repetition_rate": "Repetition rate",
    "prolongation_rate": "Prolongation rate",
    "long_pauses_per_min": "Long pauses (/min)",
    "flagged_sound_count": "Flagged speech sounds",
    "dysarthria_probability": "P(dysarthria) - TORGO acoustic model",
}


def severity_label(level: int) -> str:
    return SEVERITY_LABELS.get(int(level), "Unknown")
