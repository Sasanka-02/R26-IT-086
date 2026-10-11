"""
Practice-quality scoring, validated and calibrated against expert ratings.

The score is a linear model over measurable features of one attempt:

    score = clip( w · x , 0, 100 )

    x = [ 1,                     intercept
          live,                  1 if live audio metrics exist (reading/pacing)
          voicing,               fraction of time the voice was active (0–1)
          pauses_per_min,        long pauses (≥3 s silence) per minute
          quiet_per_min,         "too quiet" warnings per minute
          rate_deviation,        |measured wpm − target wpm| / target wpm (0–1)
          rating,                self-rating: easy +1, okay 0, hard −1
          short_attempt ]        1 if the attempt lasted < 15 s

Where the weights come from
---------------------------
* PRIOR_WEIGHTS are the starting values (documented in the viva guide).
  They are only a starting point, not a final answer.
* Therapists rate attempts on a 1–5 clinical scale (mapped to 0–100).
  Once MIN_RATINGS ratings exist, the weights are re-estimated from that
  evidence with ridge regression shrunk towards the prior:

      w = (XᵀX + λI)⁻¹ (Xᵀy + λ·w_prior)

  With few ratings the model stays close to the prior; as ratings
  accumulate the evidence dominates. Leave-one-out cross-validation
  reports how well each model predicts an unseen expert rating.
* The "strong" and "weak" thresholds used by the level engine are chosen
  as the cut-offs that best separate expert-rated good (4–5) from not-good
  attempts (balanced accuracy), instead of being fixed numbers.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.therapy.progress_store import all_records

FEATURES = [
    "intercept",
    "live",
    "voicing",
    "pauses_per_min",
    "quiet_per_min",
    "rate_deviation",
    "rating",
    "short_attempt",
]

FEATURE_LABELS = {
    "intercept": "Base score",
    "live": "Live-audio exercise",
    "voicing": "Voice active (fraction of time)",
    "pauses_per_min": "Long pauses per minute",
    "quiet_per_min": "Too-quiet warnings per minute",
    "rate_deviation": "Speech-rate deviation from target",
    "rating": "Self-rating (easy +1 / hard −1)",
    "short_attempt": "Attempt shorter than 15 s",
}

PRIOR_WEIGHTS = {
    "intercept": 72.0,
    "live": -32.0,
    "voicing": 85.0,
    "pauses_per_min": -10.0,
    "quiet_per_min": -4.0,
    "rate_deviation": -30.0,
    "rating": 12.0,
    "short_attempt": -15.0,
}
PRIOR_THRESHOLDS = {"strong": 75, "weak": 45}

SHORT_ATTEMPT_SECONDS = 15
RIDGE_LAMBDA = 4.0
MIN_RATINGS = 8
MIN_PER_CLASS = 3

RATING_VALUE = {"easy": 1.0, "ok": 0.0, "hard": -1.0}

CALIBRATION_FILE = Path(__file__).resolve().parents[2] / "data" / "calibration.json"
_lock = threading.Lock()


# --- Features ------------------------------------------------------------

def extract_features(attempt: dict) -> dict[str, float]:
    duration = float(attempt.get("duration_seconds") or 0)
    minutes = max(duration / 60, 0.25)
    ratio = attempt.get("speaking_ratio")
    live = ratio is not None
    wpm, target = attempt.get("measured_wpm"), attempt.get("target_wpm")
    rate_dev = min(1.0, abs(wpm - target) / target) if live and wpm and target else 0.0
    return {
        "intercept": 1.0,
        "live": 1.0 if live else 0.0,
        "voicing": float(ratio) if live else 0.0,
        "pauses_per_min": (attempt.get("long_pauses", 0) / minutes) if live else 0.0,
        "quiet_per_min": (attempt.get("quiet_warnings", 0) / minutes) if live else 0.0,
        "rate_deviation": rate_dev,
        "rating": RATING_VALUE.get(attempt.get("self_rating", "ok"), 0.0),
        "short_attempt": 1.0 if duration < SHORT_ATTEMPT_SECONDS else 0.0,
    }


def _vector(features: dict[str, float]) -> np.ndarray:
    return np.array([features[f] for f in FEATURES], dtype=float)


def _predict(weights: np.ndarray, x: np.ndarray) -> float:
    return float(np.clip(weights @ x, 0, 100))


def expert_to_score(rating: int) -> float:
    """1–5 clinical rating -> 0–100 on the same scale as the model."""
    return (rating - 1) * 25.0


# --- Fitting ---------------------------------------------------------------

def _prior_vector() -> np.ndarray:
    return np.array([PRIOR_WEIGHTS[f] for f in FEATURES], dtype=float)


def fit_weights(X: np.ndarray, y: np.ndarray, lam: float = RIDGE_LAMBDA) -> np.ndarray:
    prior = _prior_vector()
    A = X.T @ X + lam * np.identity(len(FEATURES))
    b = X.T @ y + lam * prior
    return np.linalg.solve(A, b)


def _loo_predictions(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    preds = np.empty(len(y))
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        w = fit_weights(X[mask], y[mask])
        preds[i] = _predict(w, X[i])
    return preds


def _metrics(pred: np.ndarray, truth: np.ndarray) -> dict:
    err = pred - truth
    r = float(np.corrcoef(pred, truth)[0, 1]) if len(truth) > 2 and np.std(pred) > 0 and np.std(truth) > 0 else None
    return {
        "mae": round(float(np.mean(np.abs(err))), 1),
        "rmse": round(float(np.sqrt(np.mean(err ** 2))), 1),
        "pearson_r": round(r, 2) if r is not None else None,
        "within_15": round(float(np.mean(np.abs(err) <= 15)) * 100),
    }


def _best_threshold(pred: np.ndarray, positive: np.ndarray, default: int) -> tuple[int, float | None]:
    """Cut-off on the model score that best matches the expert's yes/no
    judgement (balanced accuracy). Falls back to the prior if one side has
    too few examples."""
    if positive.sum() < MIN_PER_CLASS or (~positive).sum() < MIN_PER_CLASS:
        return default, None
    best_t, best_acc = default, -1.0
    for t in range(30, 96):
        said_yes = pred >= t
        tpr = np.mean(said_yes[positive])
        tnr = np.mean(~said_yes[~positive])
        acc = (tpr + tnr) / 2
        if acc > best_acc + 1e-9:
            best_t, best_acc = t, acc
    return best_t, round(float(best_acc) * 100)


def rated_attempts() -> list[dict]:
    rated = []
    for user_id, records in all_records().items():
        for r in records:
            if r.get("expert"):
                rated.append({**r, "user_id": user_id})
    return rated


def calibrate() -> dict:
    """Re-estimates weights and thresholds from all expert ratings and saves them."""
    rated = rated_attempts()
    n = len(rated)
    prior = _prior_vector()
    result: dict = {
        "fitted_at": datetime.now(timezone.utc).isoformat(),
        "n_ratings": n,
        "min_ratings": MIN_RATINGS,
        "ridge_lambda": RIDGE_LAMBDA,
        "active": "prior",
        "weights": dict(PRIOR_WEIGHTS),
        "thresholds": dict(PRIOR_THRESHOLDS),
        "threshold_accuracy": {"strong": None, "weak": None},
        "validation": None,
    }
    if n >= 2:
        X = np.array([_vector(extract_features(r)) for r in rated])
        y = np.array([expert_to_score(r["expert"]["rating"]) for r in rated])
        shown = np.array([float(r["score"]) for r in rated])
        prior_pred = np.array([_predict(prior, x) for x in X])
        validation = {
            "shown_scores": _metrics(shown, y),
            "prior_model": _metrics(prior_pred, y),
            "calibrated_model_loo": None,
        }
        if n >= MIN_RATINGS:
            weights = fit_weights(X, y)
            validation["calibrated_model_loo"] = _metrics(_loo_predictions(X, y), y)
            pred = np.array([_predict(weights, x) for x in X])
            ratings = np.array([r["expert"]["rating"] for r in rated])
            strong, strong_acc = _best_threshold(pred, ratings >= 4, PRIOR_THRESHOLDS["strong"])
            weak_cut, weak_acc = _best_threshold(pred, ratings >= 3, PRIOR_THRESHOLDS["weak"])
            result.update(
                active="calibrated",
                weights={f: round(float(w), 2) for f, w in zip(FEATURES, weights)},
                thresholds={"strong": strong, "weak": min(weak_cut, strong - 5)},
                threshold_accuracy={"strong": strong_acc, "weak": weak_acc},
            )
        result["validation"] = validation

    with _lock:
        CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        CALIBRATION_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def current_calibration() -> dict:
    with _lock:
        if CALIBRATION_FILE.exists():
            try:
                return json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {
        "active": "prior",
        "n_ratings": 0,
        "min_ratings": MIN_RATINGS,
        "weights": dict(PRIOR_WEIGHTS),
        "thresholds": dict(PRIOR_THRESHOLDS),
        "threshold_accuracy": {"strong": None, "weak": None},
        "validation": None,
    }


def thresholds() -> dict:
    return current_calibration()["thresholds"]


def score_with_breakdown(attempt: dict) -> tuple[int, list[dict]]:
    """Score plus each feature's contribution, so the result is explainable."""
    weights = current_calibration()["weights"]
    feats = extract_features(attempt)
    parts = [
        {
            "feature": f,
            "label": FEATURE_LABELS[f],
            "value": round(feats[f], 3),
            "weight": weights[f],
            "points": round(feats[f] * weights[f], 1),
        }
        for f in FEATURES
        if feats[f] != 0
    ]
    raw = sum(p["points"] for p in parts)
    return int(round(max(0.0, min(100.0, raw)))), parts


def model_report() -> dict:
    """Everything the evidence page shows about the scoring model."""
    cal = current_calibration()
    return {
        **cal,
        "features": [
            {
                "feature": f,
                "label": FEATURE_LABELS[f],
                "prior": PRIOR_WEIGHTS[f],
                "current": cal["weights"][f],
            }
            for f in FEATURES
        ],
        "prior_thresholds": PRIOR_THRESHOLDS,
    }
