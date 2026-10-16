"""
SO5 - Differentially private cohort report.

The treating therapist sees each student's exact results. Anything that
leaves the clinic — a cohort summary for researchers or a clinic manager —
is released through the Laplace mechanism instead, so no single practice
attempt can be inferred from it.

Privacy unit: one saved practice attempt (event-level DP). Each attempt
falls in exactly one bucket of a histogram, so a whole histogram costs ε
once (parallel composition); separate statistics add up (sequential
composition). The total ε for one release is split equally across the
statistic groups below and recorded in the budget ledger.

Releases are cached per data snapshot and ε: asking again for the same
data returns the same noisy numbers, so repeated requests cannot average
the noise away or drain the budget.

The accuracy table shows the expected absolute error at several ε values,
estimated by Monte-Carlo, which makes the privacy/accuracy trade-off
explicit.
"""

import hashlib

import numpy as np

from app.therapy.adaptive import LEVELS, LEVEL_LABELS, level_state
from app.therapy.privacy import budget_ledger, privatize_statistic
from app.therapy.progress_store import all_records
from app.therapy.therapist_store import get_settings
from app.therapy.user_store import age_group_of

LEDGER_ID = "cohort-report"
GROUPS = 4  # exercises-by-type histogram, level histogram, mean score, score-band histogram
TYPE_LABELS = {
    "reading": "Reading",
    "pacing": "Pacing",
    "daf": "DAF",
    "picture": "Picture description",
    "words": "Word practice",
    "roleplay": "Role-plays & talks",
}
SCORE_BANDS = [(0, 45, "Below 45"), (45, 65, "45–64"), (65, 80, "65–79"), (80, 101, "80–100")]
EPSILON_OPTIONS = [0.25, 0.5, 1.0, 2.0, 5.0]

_cache: dict[tuple[str, float], dict] = {}


def _true_stats() -> tuple[dict, str]:
    data = all_records()
    records = [r for recs in data.values() for r in recs]
    fingerprint = hashlib.sha256(
        "|".join(sorted(r["id"] for r in records)).encode()
    ).hexdigest()[:16]
    levels = {lvl: 0 for lvl in LEVELS}
    for user_id, recs in data.items():
        levels[level_state(recs, get_settings(user_id)["level_override"], age_group_of(user_id))["level"]] += 1
    scores = [r["score"] for r in records]
    stats = {
        "students": len(data),
        "attempts": len(records),
        "by_type": {t: sum(1 for r in records if r["exercise_type"] == t) for t in TYPE_LABELS},
        "levels": levels,
        "mean_score": float(np.mean(scores)) if scores else 0.0,
        "score_bands": {
            label: sum(1 for s in scores if lo <= s < hi) for lo, hi, label in SCORE_BANDS
        },
    }
    return stats, fingerprint


def _noisy(stats: dict, epsilon: float, rng: np.random.Generator) -> dict:
    eps = epsilon / GROUPS
    n = max(stats["attempts"], 1)

    def count(v: int, sensitivity: float = 1.0) -> int:
        return max(0, int(round(privatize_statistic(v, sensitivity, eps, rng))))

    return {
        "by_type": {k: count(v) for k, v in stats["by_type"].items()},
        # One attempt can move one student to another level: L1 sensitivity 2.
        "levels": {k: count(v, 2.0) for k, v in stats["levels"].items()},
        # Mean of n bounded scores (0–100): one attempt changes it by at most 100/n.
        "mean_score": round(float(np.clip(privatize_statistic(stats["mean_score"], 100 / n, eps, rng), 0, 100)), 1),
        "score_bands": {k: count(v) for k, v in stats["score_bands"].items()},
    }


def accuracy_table(stats: dict, trials: int = 400, seed: int = 1) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for eps in EPSILON_OPTIONS:
        count_err, mean_err = [], []
        for _ in range(trials):
            noisy = _noisy(stats, eps, rng)
            count_err.extend(abs(noisy["by_type"][k] - v) for k, v in stats["by_type"].items())
            mean_err.append(abs(noisy["mean_score"] - stats["mean_score"]))
        rows.append(
            {
                "epsilon": eps,
                "count_error": round(float(np.mean(count_err)), 1),
                "mean_score_error": round(float(np.mean(mean_err)), 1),
            }
        )
    return rows


def release(epsilon: float) -> dict:
    stats, fingerprint = _true_stats()
    key = (fingerprint, epsilon)
    if key not in _cache:
        rng = np.random.default_rng(int(fingerprint, 16) % (2**32) + int(epsilon * 1000))
        _cache[key] = _noisy(stats, epsilon, rng)
        budget_ledger.spend(LEDGER_ID, epsilon)
    noisy = _cache[key]
    return {
        "epsilon": epsilon,
        "epsilon_per_group": round(epsilon / GROUPS, 3),
        "students": stats["students"],
        "attempts_note": "Counts are noisy; small cohorts are heavily perturbed by design.",
        "by_type": [{"label": TYPE_LABELS[k], "value": v} for k, v in noisy["by_type"].items()],
        "levels": [{"label": LEVEL_LABELS[k], "value": v} for k, v in noisy["levels"].items()],
        "mean_score": noisy["mean_score"],
        "score_bands": [{"label": k, "value": v} for k, v in noisy["score_bands"].items()],
        "accuracy": accuracy_table(stats),
        "budget": budget_ledger.status(LEDGER_ID),
        "epsilon_options": EPSILON_OPTIONS,
    }
