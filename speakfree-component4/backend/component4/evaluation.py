"""
Evidence for the viva / report - how well Component 4 works, measured (storage-agnostic).

1. EXPERT AGREEMENT  therapists rate attempts 1-5. Each rating maps to the score scale
                     (1 -> 0, 2 -> 25, 3 -> 50, 4 -> 75, 5 -> 100) and is compared with the app's
                     practice score: MAE, Pearson r and "strong" agreement (score >= 75 vs rating >= 4).
2. RECALIBRATION     the scoring weights re-estimated from those ratings with ridge regression
                     shrunk towards the current weights:
                         w = (XᵀX + λI)⁻¹ (Xᵀy + λ·w₀)          λ = 4
                     reported with leave-one-out predictions, so the gain is not overfitted.
                     The result is a proposal - the live weights only change in scoring.py.
3. INTER-RATER       weighted Cohen's kappa where two therapists rated the same attempt.
4. PLAN REVIEW       therapists judge a generated plan appropriate / partly / not appropriate.
5. USABILITY         System Usability Scale (SUS): 10 items on a 1-5 scale,
                         item = (a - 1) for odd items, (5 - a) for even items;  SUS = 2.5 · Σ item
                     68 is the usual benchmark.
"""
from __future__ import annotations

import math

import numpy as np

from .scoring import FEATURE_LABELS, FEATURES, THRESHOLDS, WEIGHTS, extract_features

RIDGE_LAMBDA = 4.0
MIN_RATINGS = 8

# ------------------------------------------------------------------------------- 1-2. agreement
def expert_to_score(rating: int) -> float:
    return (int(rating) - 1) * 25.0


def _metrics(pred: np.ndarray, truth: np.ndarray) -> dict:
    err = np.abs(pred - truth)
    r = float(np.corrcoef(pred, truth)[0, 1]) if len(pred) > 2 and np.std(pred) > 0 and np.std(truth) > 0 else None
    return {"mae": round(float(err.mean()), 1), "pearson_r": round(r, 3) if r is not None else None,
            "within_15": round(100 * float((err <= 15).mean()), 1)}


def _strong_agreement(scores: np.ndarray, ratings: np.ndarray) -> float:
    return round(100 * float(((scores >= THRESHOLDS["strong"]) == (ratings >= 4)).mean()), 1)


def fit_ridge(X: np.ndarray, y: np.ndarray, prior: np.ndarray, lam: float = RIDGE_LAMBDA) -> np.ndarray:
    eye = np.eye(X.shape[1])
    return np.linalg.solve(X.T @ X + lam * eye, X.T @ y + lam * prior)


def agreement(rated: list[dict]) -> dict:
    """rated: [{record (attempt dict), score, rating}] - one entry per (attempt, rater)."""
    n = len(rated)
    out: dict = {"n": n, "min_ratings": MIN_RATINGS, "attempts": len({id(r["record"]) for r in rated})}
    if n == 0:
        return {**out, "current": None, "calibrated": None, "weights": None}
    scores = np.array([float(r["score"]) for r in rated])
    ratings = np.array([int(r["rating"]) for r in rated])
    truth = np.array([expert_to_score(x) for x in ratings])
    out["current"] = {**_metrics(scores, truth), "strong_agreement": _strong_agreement(scores, ratings)}
    out["rating_counts"] = {str(k): int((ratings == k).sum()) for k in range(1, 6)}
    if n < MIN_RATINGS:
        return {**out, "calibrated": None, "weights": None}

    X = np.array([[extract_features(r["record"])[f] for f in FEATURES] for r in rated])
    prior = np.array([WEIGHTS[f] for f in FEATURES])
    loo = np.zeros(n)
    for i in range(n):
        keep = np.arange(n) != i
        w = fit_ridge(X[keep], truth[keep], prior)
        loo[i] = float(np.clip(X[i] @ w, 0, 100))
    w_all = fit_ridge(X, truth, prior)
    out["calibrated"] = {**_metrics(loo, truth), "strong_agreement": _strong_agreement(loo, ratings),
                         "method": f"ridge towards current weights (λ = {RIDGE_LAMBDA}), leave-one-out"}
    out["weights"] = [{"feature": f, "label": FEATURE_LABELS[f], "current": WEIGHTS[f], "calibrated": round(float(w), 2)}
                      for f, w in zip(FEATURES, w_all)]
    return out


# ------------------------------------------------------------------------------- 3. inter-rater
def weighted_kappa(a: list[int], b: list[int], k: int = 5) -> float | None:
    """Quadratic-weighted Cohen's kappa for two raters on a 1..k scale."""
    if len(a) < 2:
        return None
    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        obs[x - 1, y - 1] += 1
    obs /= obs.sum()
    expected = np.outer(obs.sum(axis=1), obs.sum(axis=0))
    w = np.array([[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)])
    denom = float((w * expected).sum())
    return round(1 - float((w * obs).sum()) / denom, 3) if denom else None


def inter_rater(ratings_by_attempt: dict[int, list[int]]) -> dict:
    """ratings_by_attempt: attempt id -> ratings from different raters (first two are compared)."""
    pairs = [(rs[0], rs[1]) for rs in ratings_by_attempt.values() if len(rs) >= 2]
    a, b = [p[0] for p in pairs], [p[1] for p in pairs]
    exact = round(100 * sum(1 for x, y in pairs if x == y) / len(pairs), 1) if pairs else None
    return {"pairs": len(pairs), "weighted_kappa": weighted_kappa(a, b), "exact_agreement": exact}


# ------------------------------------------------------------------------------- 4. plan review
PLAN_VERDICTS = {"appropriate": "Appropriate", "partly": "Partly appropriate", "not_appropriate": "Not appropriate"}


def plan_review_stats(verdicts: list[str]) -> dict:
    n = len(verdicts)
    counts = {v: sum(1 for x in verdicts if x == v) for v in PLAN_VERDICTS}
    return {"n": n, "counts": counts, "labels": PLAN_VERDICTS,
            "appropriate_pct": round(100 * counts["appropriate"] / n) if n else None,
            "acceptable_pct": round(100 * (counts["appropriate"] + counts["partly"]) / n) if n else None}


# ------------------------------------------------------------------------------- 5. usability (SUS)
SUS_ITEMS = [
    "I think that I would like to use SpeakFree frequently.",
    "I found SpeakFree unnecessarily complex.",
    "I thought SpeakFree was easy to use.",
    "I think that I would need the support of a technical person to be able to use SpeakFree.",
    "I found the various functions in SpeakFree were well integrated.",
    "I thought there was too much inconsistency in SpeakFree.",
    "I would imagine that most people would learn to use SpeakFree very quickly.",
    "I found SpeakFree very cumbersome to use.",
    "I felt very confident using SpeakFree.",
    "I needed to learn a lot of things before I could get going with SpeakFree.",
]
SUS_BENCHMARK = 68
SUS_BANDS = [(85, "Excellent"), (71, "Good"), (51, "OK"), (0, "Poor")]
SUS_INVITE_AFTER = 3  # exercises completed before the survey is offered


def sus_score(answers: list[int]) -> float:
    if len(answers) != len(SUS_ITEMS) or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("SUS needs 10 answers between 1 and 5")
    return sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers)) * 2.5


def sus_band(score: float) -> str:
    return next(label for cutoff, label in SUS_BANDS if score >= cutoff)


def _stats(scores: list[float]) -> dict:
    n = len(scores)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95": None, "band": None}
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    half = 1.96 * sd / math.sqrt(n) if n > 1 else None
    return {"n": n, "mean": round(mean, 1), "sd": round(sd, 1),
            "ci95": [round(mean - half, 1), round(mean + half, 1)] if half is not None else None, "band": sus_band(mean)}


def sus_summary(responses: list[dict]) -> dict:
    """responses: [{role, answers, score, comment, submitted_at}]"""
    roles = sorted({r["role"] for r in responses})
    return {
        "overall": _stats([r["score"] for r in responses]),
        "by_role": {role: _stats([r["score"] for r in responses if r["role"] == role]) for role in roles},
        "benchmark": SUS_BENCHMARK,
        "items": [{"number": i + 1, "text": t, "positive": i % 2 == 0,
                   "mean_answer": round(sum(r["answers"][i] for r in responses) / len(responses), 2) if responses else None}
                  for i, t in enumerate(SUS_ITEMS)],
        "comments": [{k: r[k] for k in ("role", "score", "comment", "submitted_at")}
                     for r in sorted(responses, key=lambda r: r["submitted_at"], reverse=True) if r.get("comment")],
    }
