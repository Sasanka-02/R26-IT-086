"""
unified_score.py
================

"Research prototype unified severity score" - combines the disorder-specific
predictions, the severity estimate, Component 2 articulation indicators and
the confidence into a single transparent result.

    {
        "severity_level": 3,
        "severity_label": "Moderate",
        "risk_level": "Medium",
        "confidence_score": 0.81
    }

The logic is fully documented below and returns a `scoring_explanation` trail.
This is NOT a clinically validated scale.
"""

from __future__ import annotations

from .common import severity_label

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"


def compute_unified_score(
    disorder_result: dict,
    severity_result: dict,
    uncertainty_result: dict,
    features: dict,
) -> dict:
    explain: list[str] = []

    predicted = disorder_result["predicted_disorder"]
    disorder_prob = disorder_result["probabilities"].get(predicted, 0.0)
    model_severity = int(severity_result["severity_level"])
    expected_level = float(severity_result.get("expected_level", model_severity))
    confidence = float(uncertainty_result["confidence_score"])

    # ---- 1. start from the severity model's level -------------------------
    level = model_severity
    explain.append(
        f"Severity model level = {model_severity} "
        f"(probability-weighted expected level {expected_level:.2f})."
    )

    # ---- 2. 'normal' disorder pulls the floor down ----------------------
    if predicted == "normal" and disorder_prob >= 0.50:
        if level > 2:
            explain.append(
                f"Predicted disorder is 'normal' (p={disorder_prob:.2f}); "
                f"capping severity at 2 (was {level})."
            )
            level = 2
        else:
            explain.append("Predicted disorder is 'normal'; severity left unchanged.")

    # ---- 3. strong Component 2 articulation impairment nudges up --------
    art = features.get("overall_articulation_indicator", 75.0)
    dys = features.get("dysarthria_probability", 0.0)
    if art <= 45.0 and level < 4 and predicted != "normal":
        explain.append(
            f"Component 2 overall articulation indicator low ({art:.0f}/100); "
            f"raising severity to {level + 1}."
        )
        level += 1
    elif dys >= 0.80 and level < 4 and predicted != "normal":
        explain.append(
            f"Component 2 dysarthria probability high ({dys:.2f}); "
            f"raising severity to {level + 1}."
        )
        level += 1

    level = max(1, min(4, level))

    # ---- 4. risk level from severity x confidence ----------------------
    if level >= 3 and confidence >= 0.50:
        risk = RISK_HIGH
    elif level >= 3:
        risk = RISK_MEDIUM
        explain.append("Severity >=3 but confidence <0.50 -> risk held at MEDIUM.")
    elif level == 2:
        risk = RISK_MEDIUM
    else:
        risk = RISK_LOW

    review = bool(uncertainty_result.get("professional_review_recommended"))
    if review:
        explain.append(
            "Low confidence / high model disagreement -> flagged for "
            "professional review (risk category retained for transparency)."
        )

    explain.append(f"Final unified severity level = {level}; risk = {risk}.")

    return {
        "severity_level": level,
        "severity_label": severity_label(level),
        "risk_level": _risk_titlecase(risk),
        "confidence_score": round(confidence, 4),
        "professional_review_recommended": review,
        "scoring_method": "research prototype unified severity score",
        "scoring_explanation": explain,
        "components_used": {
            "disorder_prediction": predicted,
            "disorder_probability": round(float(disorder_prob), 4),
            "severity_model_level": model_severity,
            "component2_overall_articulation_indicator": round(float(art), 2),
            "component2_dysarthria_probability": round(float(dys), 4),
            "confidence_score": round(confidence, 4),
        },
    }


def _risk_titlecase(risk: str) -> str:
    return {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"}[risk]
