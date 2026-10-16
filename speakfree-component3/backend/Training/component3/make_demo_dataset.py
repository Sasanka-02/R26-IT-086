"""
make_demo_dataset.py
====================

Generates a **clearly-labelled SYNTHETIC DEMO dataset** for developing and
demonstrating the Component 3 pipeline.

WHY THIS EXISTS
---------------
The repository's only real research dataset is TORGO, which is labelled
`healthy` / `dysarthria` ONLY. It contains NO:
    - 4-way disorder labels (normal / stuttering / dysarthria / articulation)
    - Level 1-4 severity labels
    - stuttering-event labels (repetition / prolongation / block)

To build and demonstrate the full multi-disorder + severity + stuttering
pipeline today, this script synthesises a dataset whose feature columns match
`component3.common.FEATURE_ORDER` (i.e. the exact fields the feature adapter
produces from real Component 2 output).

*** THIS IS DEMO DATA. ***
Every row carries `data_source = "SYNTHETIC_DEMO"`. Models trained on it MUST
NOT be presented as clinically validated or as producing research-valid
accuracy. It exists to prove the ML pipeline is real (real train/test split,
real RandomForest.fit / predict / predict_proba), not to make clinical claims.

The real research model (binary dysarthria, TORGO, speaker-independent
GroupKFold) is trained separately by `train_dysarthria_real_torgo.py`.
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import DEMO_DATASET_CSV  # noqa: F401,E402  (also bootstraps sys.path)

import numpy as np  # noqa: E402
import pandas as pd

from component3.common import FEATURE_ORDER, DISORDER_CLASSES, STUTTER_EVENTS

SEED = 42
N_PER_DISORDER = 650  # -> ~2600 rows total


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def _clip(v, lo, hi):
    return float(np.clip(v, lo, hi))


def _sample_severity(rng: np.random.Generator, disorder: str) -> int:
    if disorder == "normal":
        return int(rng.choice([1, 2], p=[0.9, 0.1]))
    # mild / moderate / severe dominate for the pathological classes
    return int(rng.choice([2, 3, 4], p=[0.4, 0.38, 0.22]))


def _row(rng: np.random.Generator, disorder: str) -> dict:
    sev = _sample_severity(rng, disorder)
    s = sev - 1  # 0..3 severity offset

    f = {name: 0.0 for name in FEATURE_ORDER}

    # ---- alignment availability (MFA is often absent) --------------------
    alignment_present = rng.random() < 0.45
    f["alignment_uncertain"] = 0.0 if alignment_present else 1.0
    f["phoneme_count"] = float(max(0, int(rng.normal(26, 6)))) if alignment_present else 0.0
    f["alignment_reliability"] = _clip(rng.normal(78, 9), 40, 98) if alignment_present else 50.0

    # ---- disorder-conditioned generation -------------------------------
    if disorder == "normal":
        dys_p = _clip(rng.beta(2, 18), 0.0, 1.0)
        f["fluency_score"] = _clip(rng.normal(92, 4), 60, 100)
        f["word_repetition_count"] = float(rng.poisson(0.3))
        f["phrase_repetition_count"] = float(rng.poisson(0.1))
        f["filler_count"] = float(rng.poisson(0.8))
        f["long_pause_count"] = float(rng.poisson(0.3))
        f["speech_rate_wpm"] = _clip(rng.normal(140, 15), 70, 220)
        f["timing_consistency"] = _clip(rng.normal(88, 5), 50, 100)
        f["duration_variation"] = _clip(rng.normal(0.30, 0.06), 0.05, 1.5)
        art = _clip(rng.normal(90, 5), 50, 100)

    elif disorder == "stuttering":
        dys_p = _clip(rng.beta(3, 12) + 0.05 * s, 0.0, 1.0)
        f["fluency_score"] = _clip(rng.normal(74 - 13 * s, 6), 5, 100)
        f["word_repetition_count"] = float(rng.poisson(1.5 + 2.2 * sev))
        f["phrase_repetition_count"] = float(rng.poisson(0.4 + 0.9 * sev))
        f["filler_count"] = float(rng.poisson(1.0 + 1.6 * sev))
        f["long_pause_count"] = float(rng.poisson(0.8 + 1.3 * sev))
        f["speech_rate_wpm"] = _clip(rng.normal(132 - 12 * s, 16), 50, 210)
        f["timing_consistency"] = _clip(rng.normal(80 - 3 * s, 7), 40, 100)
        f["duration_variation"] = _clip(rng.normal(0.38 + 0.05 * s, 0.08), 0.05, 1.6)
        art = _clip(rng.normal(80 - 4 * s, 7), 40, 100)

    elif disorder == "dysarthria":
        dys_p = _clip(rng.normal(0.5 + 0.12 * s, 0.10), 0.05, 0.99)
        f["fluency_score"] = _clip(rng.normal(72 - 6 * s, 8), 10, 100)
        f["word_repetition_count"] = float(rng.poisson(0.5 + 0.4 * sev))
        f["phrase_repetition_count"] = float(rng.poisson(0.2))
        f["filler_count"] = float(rng.poisson(0.6 + 0.5 * sev))
        f["long_pause_count"] = float(rng.poisson(0.6 + 0.8 * sev))
        f["speech_rate_wpm"] = _clip(rng.normal(120 - 14 * s, 15), 40, 190)
        f["timing_consistency"] = _clip(rng.normal(74 - 12 * s, 8), 20, 100)
        f["duration_variation"] = _clip(rng.normal(0.45 + 0.18 * s, 0.10), 0.1, 2.0)
        art = _clip(rng.normal(76 - 13 * s, 8), 15, 100)

    else:  # articulation
        dys_p = _clip(rng.normal(0.42 + 0.06 * s, 0.10), 0.05, 0.95)
        f["fluency_score"] = _clip(rng.normal(80 - 5 * s, 7), 20, 100)
        f["word_repetition_count"] = float(rng.poisson(0.4 + 0.3 * sev))
        f["phrase_repetition_count"] = float(rng.poisson(0.15))
        f["filler_count"] = float(rng.poisson(0.6 + 0.4 * sev))
        f["long_pause_count"] = float(rng.poisson(0.4 + 0.5 * sev))
        f["speech_rate_wpm"] = _clip(rng.normal(128 - 8 * s, 16), 50, 200)
        f["timing_consistency"] = _clip(rng.normal(80 - 9 * s, 8), 25, 100)
        f["duration_variation"] = _clip(rng.normal(0.38 + 0.12 * s, 0.09), 0.08, 1.8)
        art = _clip(rng.normal(80 - 14 * s, 8), 15, 100)

    # ---- derived Component-2-style fields ------------------------------
    f["dysarthria_probability"] = dys_p
    f["dysarthria_risk_score"] = _clip(dys_p * 100 + rng.normal(0, 3), 0, 100)
    f["risk_level_ordinal"] = float(
        2 if dys_p >= 0.70 else (1 if dys_p >= 0.40 else 0)
    )

    total_disfluency = (
        f["word_repetition_count"]
        + f["phrase_repetition_count"]
        + f["filler_count"]
        + f["long_pause_count"]
    )
    f["total_disfluency_indicators"] = float(total_disfluency)

    approx_words = max(8.0, f["speech_rate_wpm"] * rng.uniform(0.25, 0.9))
    f["repetition_rate"] = _clip(
        (f["word_repetition_count"] + f["phrase_repetition_count"]) / approx_words,
        0.0, 1.0,
    )
    f["filler_rate"] = _clip(f["filler_count"] / approx_words, 0.0, 1.0)

    if f["alignment_uncertain"] == 0.0:
        f["overall_articulation_indicator"] = art
        f["phoneme_consistency"] = _clip(art + rng.normal(0, 5), 0, 100)
        f["acoustic_model_component"] = _clip((1 - dys_p) * 100 + rng.normal(0, 5), 0, 100)
    else:
        # MFA absent -> C2 leaves these null -> adapter imputes the defaults
        f["overall_articulation_indicator"] = 75.0
        f["phoneme_consistency"] = 75.0
        f["acoustic_model_component"] = 75.0
        f["timing_consistency"] = 75.0
        f["duration_variation"] = 0.35

    # ---- stuttering event multi-labels --------------------------------
    rep_logit = -1.4 + 0.55 * f["word_repetition_count"] + 0.7 * f["phrase_repetition_count"]
    pro_logit = -2.2 + (1.1 if disorder == "stuttering" else 0.0) + 0.45 * s + rng.normal(0, 0.6)
    blk_logit = (
        -2.0
        + 0.5 * f["long_pause_count"]
        + (0.9 if disorder == "stuttering" else 0.0)
        - 0.015 * (f["speech_rate_wpm"] - 120)
        + rng.normal(0, 0.6)
    )
    if disorder == "stuttering":
        rep_logit += 0.6
    p_rep = _sigmoid(rep_logit + rng.normal(0, 0.5))
    p_pro = _sigmoid(pro_logit)
    p_blk = _sigmoid(blk_logit)

    row = dict(f)
    row["disorder"] = disorder
    row["severity_level"] = int(1 if disorder == "normal" and sev == 1 else sev)
    row["stutter_repetition"] = int(rng.random() < p_rep)
    row["stutter_prolongation"] = int(rng.random() < p_pro)
    row["stutter_block"] = int(rng.random() < p_blk)
    row["data_source"] = "SYNTHETIC_DEMO"
    return row


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for disorder in DISORDER_CLASSES:
        for _ in range(N_PER_DISORDER):
            rows.append(_row(rng, disorder))
    df = pd.DataFrame(rows)
    ordered = (
        FEATURE_ORDER
        + ["disorder", "severity_level"]
        + [f"stutter_{e}" for e in STUTTER_EVENTS]
        + ["data_source"]
    )
    return df[ordered]


def main():
    df = build()
    df.to_csv(DEMO_DATASET_CSV, index=False)
    print(f"[make_demo_dataset] wrote {len(df)} rows -> {DEMO_DATASET_CSV}")
    print("\nDisorder distribution:")
    print(df["disorder"].value_counts())
    print("\nSeverity distribution:")
    print(df["severity_level"].value_counts().sort_index())
    print("\nStuttering-event positives:")
    for e in STUTTER_EVENTS:
        print(f"  {e:14s}: {int(df[f'stutter_{e}'].sum())}")
    print("\n*** data_source = SYNTHETIC_DEMO (not clinically validated) ***")


if __name__ == "__main__":
    main()
