"""
make_demo_dataset.py  (v2 - integrated feature contract)
========================================================

Generates a **clearly-labelled SYNTHETIC DEMO dataset** for training the stage-2 Component 3
models (disorder classifier, severity estimator, stuttering multi-label model).

WHY THIS EXISTS
---------------
No public dataset available to the project carries all of: 4-way disorder labels
(normal / stuttering / dysarthria / articulation), Level 1-4 severity labels and stuttering
event labels for the SAME speakers, with the SAME features Components 1 and 2 produce. TORGO
(the real corpus used for the stage-1 acoustic model) is labelled healthy / dysarthria only.

This script synthesises rows whose columns match `component3.common.FEATURE_ORDER` exactly,
with disorder- and severity-conditioned distributions chosen from the clinical literature's
qualitative descriptions. The `dysarthria_probability` column is NOT invented: it is sampled
from the stage-1 TORGO model's real out-of-fold predictions (per speaker, by TORGO severity).


  stuttering   -> repetitions, prolongations and blocks rise with severity; fluency falls
  dysarthria   -> slow articulation rate, low ASR confidence / clear-word ratio, high P(dys)
  articulation -> flagged speech sounds, lower pronunciation score, fluency mostly normal
  normal       -> high scores, few events

*** THIS IS DEMO DATA. ***  Every row carries data_source = "SYNTHETIC_DEMO". Models trained on
it prove that the ML pipeline is real (fit / predict_proba / held-out metrics); they MUST NOT be
reported as clinically validated. Replace with real labelled sessions when they exist and
re-run train_all.py.
"""

import os as _os, sys as _sys  # noqa: E401
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from _paths import DEMO_DATASET_CSV, TORGO_OOF_CSV  # noqa: E402  (also bootstraps sys.path)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from component3.common import DISORDER_CLASSES, FEATURE_ORDER, STUTTER_EVENTS  # noqa: E402

SEED = 42
N_PER_DISORDER = 900
WINDOWS_PER_SESSION = 12  # a 5-recording screening yields up to 15 acoustic windows

# TORGO speaker groups by clinical severity (TORGO documentation). Their OUT-OF-FOLD stage-1
# probabilities are what the stage-1 model really outputs for unseen speakers of that kind.
TORGO_SEVERITY_SPEAKERS = {
    2: ["F03", "F04", "M03"],            # mild
    3: ["M05", "F03", "M03"],            # mild-moderate / moderate
    4: ["F01", "M01", "M02", "M04"],     # severe
}
_OOF = None


def _oof():
    global _OOF
    if _OOF is None:
        _OOF = pd.read_csv(TORGO_OOF_CSV) if TORGO_OOF_CSV.exists() else False
    return _OOF


def _sample_dysarthria_probability(rng: np.random.Generator, disorder: str, sev: int) -> float:
    """
    Session-level P(dysarthria): mean of WINDOWS_PER_SESSION real out-of-fold stage-1
    probabilities from ONE TORGO speaker (dysarthric speakers of matching severity for the
    dysarthria class, control speakers for every other class). Grounds the cascade's key
    feature in real data; falls back to a beta draw if the OOF file is missing.
    """
    oof = _oof()
    if oof is False:
        return float(rng.beta(4 + 2 * (sev - 1), 3) if disorder == "dysarthria" else rng.beta(3, 5))
    if disorder == "dysarthria":
        speaker = rng.choice(TORGO_SEVERITY_SPEAKERS[max(2, sev)])
    else:
        speaker = rng.choice(sorted(oof.loc[oof.label == 0, "speaker_id"].unique()))
    probs = oof.loc[oof.speaker_id == speaker, "probability"].to_numpy()
    return float(rng.choice(probs, size=WINDOWS_PER_SESSION, replace=True).mean())


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _clip(v, lo, hi):
    return float(np.clip(v, lo, hi))


def _severity(rng: np.random.Generator, disorder: str) -> int:
    if disorder == "normal":
        return int(rng.choice([1, 2], p=[0.88, 0.12]))
    return int(rng.choice([2, 3, 4], p=[0.40, 0.37, 0.23]))


def _row(rng: np.random.Generator, disorder: str) -> dict:
    sev = _severity(rng, disorder)
    s = sev - 1  # 0..3
    n = rng.normal

    # healthy baseline, then disorder-specific deviations
    f = {
        "articulation_score": n(90, 4),
        "clear_word_ratio": n(0.95, 0.025),
        "kept_token_confidence": n(0.88, 0.04),
        "asr_confidence": n(88, 4),
        "dysfluency_ratio": n(0.05, 0.025),
        "fluency_score": n(87, 5),
        "pronunciation_score": n(87, 5),
        "speech_rate_wpm": n(128, 18),
        "articulation_rate_sps": n(4.3, 0.5),
        "pause_rate_per_min": n(9, 3),
        "longest_pause_sec": n(0.9, 0.35),
        "filler_rate": abs(n(0.02, 0.015)),
        "repetition_rate": abs(n(0.008, 0.008)),
        "prolongation_rate": abs(n(0.005, 0.005)),
        "long_pauses_per_min": abs(n(0.6, 0.5)),
        "flagged_sound_count": float(rng.poisson(0.4)),
        "dysarthria_probability": _sample_dysarthria_probability(rng, disorder, sev),
    }

    if disorder == "normal" and sev == 2:  # borderline typical speaker
        f["fluency_score"] -= 6
        f["articulation_score"] -= 5
        f["filler_rate"] += 0.02

    elif disorder == "stuttering":
        f["repetition_rate"] += abs(n(0.03 + 0.035 * s, 0.015))
        f["prolongation_rate"] += abs(n(0.015 + 0.02 * s, 0.01))
        f["long_pauses_per_min"] += abs(n(1.0 + 1.4 * s, 0.7))
        f["filler_rate"] += abs(n(0.02 + 0.02 * s, 0.012))
        f["fluency_score"] -= abs(n(10 + 11 * s, 5))
        f["dysfluency_ratio"] += abs(n(0.04 + 0.05 * s, 0.02))
        f["clear_word_ratio"] -= abs(n(0.03 + 0.04 * s, 0.02))
        f["articulation_score"] -= abs(n(3 + 5 * s, 3))
        f["speech_rate_wpm"] -= abs(n(10 + 12 * s, 8))
        f["longest_pause_sec"] += abs(n(0.8 + 0.7 * s, 0.4))
        f["pause_rate_per_min"] += abs(n(3 + 3 * s, 2))

    elif disorder == "dysarthria":
        # mild dysarthria often keeps ASR-based scores near normal - the acoustic stage-1
        # probability carries most of the evidence; deviations grow with severity
        d = s - 1  # 0 (mild) .. 2 (severe)
        f["articulation_rate_sps"] -= abs(n(0.4 + 0.7 * d, 0.3))
        f["speech_rate_wpm"] -= abs(n(10 + 18 * d, 8))
        f["kept_token_confidence"] -= abs(n(0.02 + 0.08 * d, 0.02))
        f["asr_confidence"] -= abs(n(2 + 9 * d, 2))
        f["clear_word_ratio"] -= abs(n(0.02 + 0.08 * d, 0.02))
        f["articulation_score"] -= abs(n(3 + 11 * d, 3))
        f["pronunciation_score"] -= abs(n(3 + 11 * d, 3))
        f["fluency_score"] -= abs(n(2 + 5 * d, 3))
        f["pause_rate_per_min"] += abs(n(1.5 + 2.5 * d, 1.5))
        f["dysfluency_ratio"] += abs(n(0.02 + 0.06 * d, 0.02))
        f["flagged_sound_count"] += float(rng.poisson(0.4 + 0.8 * d))

    else:  # articulation
        f["flagged_sound_count"] += float(rng.poisson(1.5 + 1.2 * s))
        f["pronunciation_score"] -= abs(n(8 + 8 * s, 4))
        f["articulation_score"] -= abs(n(5 + 6 * s, 3))
        f["clear_word_ratio"] -= abs(n(0.03 + 0.04 * s, 0.02))
        f["kept_token_confidence"] -= abs(n(0.03 + 0.04 * s, 0.02))
        f["asr_confidence"] -= abs(n(3 + 4 * s, 2))
        f["dysfluency_ratio"] += abs(n(0.02 + 0.03 * s, 0.015))

    bounds = {
        "articulation_score": (0, 100), "clear_word_ratio": (0, 1), "kept_token_confidence": (0, 1),
        "asr_confidence": (0, 100), "dysfluency_ratio": (0, 1), "fluency_score": (0, 100),
        "pronunciation_score": (0, 100), "speech_rate_wpm": (30, 220), "articulation_rate_sps": (1.0, 7.5),
        "pause_rate_per_min": (0, 60), "longest_pause_sec": (0.25, 8), "filler_rate": (0, 1),
        "repetition_rate": (0, 1), "prolongation_rate": (0, 1), "long_pauses_per_min": (0, 20),
        "flagged_sound_count": (0, 12), "dysarthria_probability": (0, 1),
    }
    f = {k: _clip(v, *bounds[k]) for k, v in f.items()}

    # ---- stuttering event multi-labels (independent heads) --------------------------------
    stut = 1.0 if disorder == "stuttering" else 0.0
    p_rep = _sigmoid(-3.0 + 55 * f["repetition_rate"] + 0.8 * stut + n(0, 0.5))
    p_pro = _sigmoid(-3.0 + 80 * f["prolongation_rate"] + 0.8 * stut + n(0, 0.5))
    p_blk = _sigmoid(-3.0 + 0.9 * f["long_pauses_per_min"] + 0.6 * stut
                     - 0.012 * (f["speech_rate_wpm"] - 120) + n(0, 0.5))

    row = dict(f)
    row["disorder"] = disorder
    row["severity_level"] = sev
    row["stutter_repetition"] = int(rng.random() < p_rep)
    row["stutter_prolongation"] = int(rng.random() < p_pro)
    row["stutter_block"] = int(rng.random() < p_blk)
    row["data_source"] = "SYNTHETIC_DEMO"
    return row


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = [_row(rng, d) for d in DISORDER_CLASSES for _ in range(N_PER_DISORDER)]
    df = pd.DataFrame(rows)
    ordered = FEATURE_ORDER + ["disorder", "severity_level"] + [f"stutter_{e}" for e in STUTTER_EVENTS] + ["data_source"]
    return df[ordered]


def main():
    df = build()
    df.to_csv(DEMO_DATASET_CSV, index=False)
    print(f"[make_demo_dataset] wrote {len(df)} rows -> {DEMO_DATASET_CSV}")
    print(df["disorder"].value_counts().to_string())
    print(df["severity_level"].value_counts().sort_index().to_string())
    for e in STUTTER_EVENTS:
        print(f"  {e:14s}: {int(df[f'stutter_{e}'].sum())} positives")
    print("*** data_source = SYNTHETIC_DEMO (not clinically validated) ***")


if __name__ == "__main__":
    main()
