"""
Differential privacy for statistics that leave the clinic (SO5) - the Laplace mechanism.

  * Applied: the cohort report (practice across ALL patients, for researchers or a clinic
    manager). Every count and mean is released as  value + Lap(sensitivity / ε)  and the ε
    spent is written to the privacy budget ledger (stored by the platform).
  * Not applied: a patient's own dashboard and the treating therapist's view - they need exact
    numbers to give therapy and stay behind the platform's access control.

Privacy unit: one saved practice attempt (event-level DP). Each attempt falls in exactly one
bucket of a histogram, so a whole histogram costs ε once (parallel composition); the separate
statistic groups add up (sequential composition), so the release's ε is split equally across them.
Releases are seeded from a fingerprint of the data + ε: asking again for the same data returns the
same noisy numbers, so repeated requests cannot average the noise away or drain the budget.

Federated learning (SO4) is a documented design only - it needs a multi-device rollout.
"""
from __future__ import annotations

import hashlib

import numpy as np

EPSILON_OPTIONS = [0.25, 0.5, 1.0, 2.0, 5.0]
BUDGET_THRESHOLD = 10.0   # total ε the clinic allows for cohort releases
GROUPS = 4                # by-type histogram, level histogram, mean score, score-band histogram
SCORE_BANDS = [(0, 45, "Below 45"), (45, 65, "45–64"), (65, 80, "65–79"), (80, 101, "80–100")]

FEDERATED_DESIGN = {
    "protocol": "FedAvg with secure aggregation",
    "framework": "Flower (flwr)",
    "round_frequency": "weekly",
    "compression": "top-k sparsification (k = 10%) + 16-bit quantisation",
    "raw_audio_leaves_device": False,
    "aggregation_weighting": "by sessions completed per client that week",
    "status": "design complete, not deployed - requires a multi-device rollout",
}


def laplace(value: float, sensitivity: float, epsilon: float, rng: np.random.Generator) -> float:
    return value + float(rng.laplace(0.0, sensitivity / max(epsilon, 1e-9)))


def fingerprint(attempt_ids: list) -> str:
    return hashlib.sha256("|".join(sorted(map(str, attempt_ids))).encode()).hexdigest()[:16]


def true_stats(records: list[dict], levels: list[int], type_labels: dict[str, str]) -> dict:
    """records: every attempt in the clinic; levels: each patient's current practice level (1-8)."""
    scores = [r["score"] for r in records]
    return {
        "patients": len(levels),
        "attempts": len(records),
        "by_type": {t: sum(1 for r in records if r["exercise_type"] == t) for t in type_labels},
        "levels": {str(b): sum(1 for lv in levels if lv == b) for b in range(1, 9)},
        "mean_score": float(np.mean(scores)) if scores else 0.0,
        "score_bands": {label: sum(1 for s in scores if lo <= s < hi) for lo, hi, label in SCORE_BANDS},
    }


def _noisy(stats: dict, epsilon: float, rng: np.random.Generator) -> dict:
    eps = epsilon / GROUPS
    n = max(stats["attempts"], 1)

    def count(v: int, sensitivity: float = 1.0) -> int:
        return max(0, int(round(laplace(v, sensitivity, eps, rng))))

    return {
        "by_type": {k: count(v) for k, v in stats["by_type"].items()},
        "levels": {k: count(v, 2.0) for k, v in stats["levels"].items()},  # one attempt can move one patient a level
        "mean_score": round(float(np.clip(laplace(stats["mean_score"], 100 / n, eps, rng), 0, 100)), 1),
        "score_bands": {k: count(v) for k, v in stats["score_bands"].items()},
    }


def accuracy_table(stats: dict, trials: int = 300, seed: int = 1) -> list[dict]:
    """Expected absolute error of the released numbers at each ε (Monte-Carlo)."""
    rng = np.random.default_rng(seed)
    rows = []
    for eps in EPSILON_OPTIONS:
        count_err, mean_err = [], []
        for _ in range(trials):
            noisy = _noisy(stats, eps, rng)
            count_err.extend(abs(noisy["by_type"][k] - v) for k, v in stats["by_type"].items())
            mean_err.append(abs(noisy["mean_score"] - stats["mean_score"]))
        rows.append({"epsilon": eps, "count_error": round(float(np.mean(count_err)), 1),
                     "mean_score_error": round(float(np.mean(mean_err)), 1)})
    return rows


def release(stats: dict, epsilon: float, data_fingerprint: str, type_labels: dict[str, str]) -> dict:
    rng = np.random.default_rng(int(data_fingerprint, 16) % (2 ** 32) + int(epsilon * 1000))
    noisy = _noisy(stats, epsilon, rng)
    return {
        "epsilon": epsilon,
        "epsilon_per_group": round(epsilon / GROUPS, 3),
        "patients": stats["patients"],
        "by_type": [{"key": k, "label": type_labels[k], "value": v} for k, v in noisy["by_type"].items()],
        "levels": [{"key": k, "label": f"Level {k}", "value": v} for k, v in noisy["levels"].items()],
        "mean_score": noisy["mean_score"],
        "score_bands": [{"key": k, "label": k, "value": v} for k, v in noisy["score_bands"].items()],
        "accuracy": accuracy_table(stats),
        "note": "Counts are noisy; small cohorts are heavily perturbed by design.",
    }


def budget_status(spent: float) -> dict:
    return {"epsilon_spent": round(spent, 4), "epsilon_threshold": BUDGET_THRESHOLD,
            "epsilon_remaining": round(max(0.0, BUDGET_THRESHOLD - spent), 4),
            "exhausted": spent >= BUDGET_THRESHOLD}


# ------------------------------------------------------------------------------- DAF calibration (SO2)
DAF_DELAYS = [50, 100, 150, 200, 300]
DAF_TARGET_WPM = 130.0


def calibrate_daf(trials: list[dict], target_wpm: float = DAF_TARGET_WPM) -> dict:
    """
    Pick the delay that minimises stutter events × deviation from a comfortable rate (proposal
    protocol); ties (e.g. no stutter events at all) go to fewer events, then the rate closest to target.
    trials: [{delay_ms, stutter_events, speech_rate_wpm}]
    """
    if not trials:
        raise ValueError("At least one trial is needed")

    def cost(t: dict) -> tuple:
        dev = abs(float(t["speech_rate_wpm"]) - target_wpm)
        return (int(t["stutter_events"]) * dev, int(t["stutter_events"]), dev)

    best = min(trials, key=cost)
    return {"recommended_delay_ms": int(best["delay_ms"]), "trials_evaluated": len(trials), "target_wpm": target_wpm,
            "trials": [{**t, "cost": round(cost(t)[0], 1)} for t in trials]}
