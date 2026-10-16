"""
unified_score.py
================

###########################################################################################
#  ★ COMPONENT 3 NOVELTY - MODEL-BASED SEVERITY CLASSIFICATION (fusion step)              #
#                                                                                         #
#  Two-stage model cascade:                                                               #
#    stage 1  TORGO RandomForest (real data)   acoustic windows -> P(dysarthria)          #
#    stage 2  RF disorder classifier            x -> P(normal|stutter|dysarthria|artic.)  #
#             RF severity estimator             x -> P(level = 1..4)                      #
#             multi-label RF (stuttering)        x -> P(repetition), P(prolong.), P(block) #
#                                                                                         #
#  Fusion (this file):                                                                    #
#    E[level]  = Σ_l l · P(level = l)                    probability-weighted level       #
#    level_0   = argmax_l P(level = l)                                                    #
#    rule 1    disorder = normal with p >= 0.5          -> level <= 2                     #
#    rule 2    A_session (C2) <= 45 or P(dys) >= 0.80   -> level + 1   (non-normal only)  #
#    risk      = High if level >= 3 and confidence >= 0.5, Medium if level = 2 (or low    #
#                confidence), Low otherwise                                               #
#  Every rule that fires is written to `scoring_explanation`, so the result is auditable.  #
###########################################################################################

This is NOT a clinically validated scale.
"""

from __future__ import annotations

from .common import severity_label

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
ARTICULATION_FLOOR = 45.0
DYSARTHRIA_HIGH = 0.80


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

    # ---- 2. 'normal' disorder caps the level -----------------------------
    if predicted == "normal" and disorder_prob >= 0.50:
        if level > 2:
            explain.append(
                f"Predicted disorder is 'normal' (p={disorder_prob:.2f}); "
                f"capping severity at 2 (was {level})."
            )
            level = 2
        else:
            explain.append("Predicted disorder is 'normal'; severity left unchanged.")

    # ---- 3. strong Component 2 / acoustic evidence nudges up ---------------
    art = features.get("articulation_score", 85.0)
    dys = features.get("dysarthria_probability", 0.0)
    if art <= ARTICULATION_FLOOR and level < 4 and predicted != "normal":
        explain.append(
            f"Component 2 articulation score low ({art:.0f}/100); raising severity to {level + 1}."
        )
        level += 1
    elif dys >= DYSARTHRIA_HIGH and level < 4 and predicted != "normal":
        explain.append(
            f"TORGO acoustic model P(dysarthria) high ({dys:.2f}); raising severity to {level + 1}."
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
        "risk_level": {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"}[risk],
        "confidence_score": round(confidence, 4),
        "professional_review_recommended": review,
        "scoring_method": "two-stage model cascade + rule-guarded fusion (research prototype)",
        "scoring_explanation": explain,
        "components_used": {
            "disorder_prediction": predicted,
            "disorder_probability": round(float(disorder_prob), 4),
            "severity_model_level": model_severity,
            "expected_level": round(expected_level, 3),
            "component2_articulation_score": round(float(art), 2),
            "stage1_dysarthria_probability": round(float(dys), 4),
            "confidence_score": round(confidence, 4),
        },
    }
