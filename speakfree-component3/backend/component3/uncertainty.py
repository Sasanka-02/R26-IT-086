"""
uncertainty.py
==============

Confidence & uncertainty estimation for the disorder prediction.

Baseline (implemented today):
    confidence_score        = max predicted probability
    confidence_band         = High (>=0.80) / Medium (0.60-0.79) / Low (<0.60)
    normalised_entropy      = H(p) / log(K)          -> 0 (certain) .. 1 (uniform)
    epistemic_std           = mean per-class std of predict_proba across the
                              RandomForest's trees  (a real ensemble-disagreement
                              estimate; a lightweight stand-in for MC-Dropout,
                              which applies to the future HuBERT model)
    temperature             = calibration temperature applied to the logits
                              (default 1.0 = uncalibrated; see apply_temperature)

`professional_review_recommended` is True when confidence is Low OR ensemble
disagreement is high.

NOTE: this is a screening confidence indicator, NOT clinical certainty.
"""

from __future__ import annotations

import math

DEFAULT_TEMPERATURE = 1.0
LOW_CONF = 0.60
HIGH_CONF = 0.80
HIGH_EPISTEMIC_STD = 0.15


def _band(conf: float) -> str:
    if conf >= HIGH_CONF:
        return "High"
    if conf >= LOW_CONF:
        return "Medium"
    return "Low"


def apply_temperature(probabilities: dict, temperature: float = DEFAULT_TEMPERATURE) -> dict:
    """
    Temperature scaling on a probability dict. T>1 softens, T<1 sharpens.
    T=1 returns the inputs unchanged. Implemented via log-prob / T + softmax.
    """
    if not probabilities or temperature is None or abs(temperature - 1.0) < 1e-9:
        return dict(probabilities)
    keys = list(probabilities)
    logits = [math.log(max(probabilities[k], 1e-12)) / max(temperature, 1e-6) for k in keys]
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    z = sum(exps)
    return {k: round(e / z, 4) for k, e in zip(keys, exps)}


def estimate_uncertainty(disorder_result: dict, temperature: float = DEFAULT_TEMPERATURE) -> dict:
    raw_probs = disorder_result.get("probabilities", {}) or {}
    calibrated = apply_temperature(raw_probs, temperature)

    values = list(calibrated.values()) if calibrated else [1.0]
    confidence = max(values) if values else 0.0

    k = max(len(values), 2)
    entropy = -sum(p * math.log(p) for p in values if p > 0)
    norm_entropy = entropy / math.log(k)

    std_map = disorder_result.get("estimator_proba_std", {}) or {}
    epistemic_std = (
        sum(std_map.values()) / len(std_map) if std_map else 0.0
    )

    band = _band(confidence)
    review = band == "Low" or epistemic_std >= HIGH_EPISTEMIC_STD

    return {
        "confidence_score": round(float(confidence), 4),
        "confidence_band": band,
        "normalised_entropy": round(float(norm_entropy), 4),
        "epistemic_std": round(float(epistemic_std), 4),
        "temperature": float(temperature),
        "calibrated_probabilities": calibrated,
        "professional_review_recommended": bool(review),
        "method": (
            "max-probability confidence + normalised entropy + RF tree-"
            "disagreement (epistemic). Temperature scaling hook present "
            f"(T={temperature}); MC-Dropout reserved for the HuBERT model."
        ),
        "note": "Screening confidence indicator - not clinical certainty.",
    }
