"""
report.py
=========

Assembles the structured clinical-screening report (the Component 3 public output contract,
consumed by Component 4 and the admin severity dashboard).

NOT a clinical diagnosis - a research screening result.
"""

from __future__ import annotations

from .common import FEATURE_LABELS, FEATURE_ORDER, MODEL_VERSION

# Plain-language therapy focus that Component 4 uses for each category.
THERAPY_FOCUS = {
    "normal": "maintenance",
    "stuttering": "fluency",
    "dysarthria": "motor_speech",
    "articulation": "speech_sounds",
}


def _recommendations(disorder: str, level: int, review: bool) -> list[str]:
    recs: list[str] = []
    if review:
        recs.append("Confidence is limited - recommend review by a qualified speech-language pathologist before any conclusion.")
    if disorder == "normal" and level <= 2:
        recs.append("No screening indicators of a speech disorder detected - maintenance practice only.")
    if disorder == "stuttering":
        recs.append("Indicators consistent with disfluency / stuttering; consider a fluency-focused assessment.")
        if level >= 3:
            recs.append("Component 4: pacing, gentle-onset and DAF practice prioritised.")
    if disorder == "dysarthria":
        recs.append("Indicators consistent with dysarthria; consider a motor-speech assessment.")
        if level >= 3:
            recs.append("Component 4: loudness, breath-support and clear-speech practice prioritised.")
    if disorder == "articulation":
        recs.append("Indicators consistent with an articulation difficulty; consider a phonological / articulation assessment.")
        recs.append("Component 4: targeted sound drills for the flagged sounds.")
    if level >= 3 and not review:
        recs.append("Severity screened as Moderate+ - professional follow-up advised.")
    if not recs:
        recs.append("Routine monitoring; re-screen if concerns persist.")
    return recs


def build_report(
    *,
    session_id: str,
    user_id: str,
    adapter_result: dict,
    disorder_result: dict,
    stuttering_result: dict,
    severity_result: dict,
    uncertainty_result: dict,
    unified_result: dict,
    component2_output: dict,
) -> dict:
    disorder = unified_result["components_used"]["disorder_prediction"]
    level = unified_result["severity_level"]
    review = unified_result["professional_review_recommended"]
    features = adapter_result["features"]
    handoff = component2_output.get("component3_input") if isinstance(component2_output.get("component3_input"), dict) else component2_output

    any_fallback = any(
        r.get("model_status", "").startswith("NOT_TRAINED")
        for r in (disorder_result, severity_result, stuttering_result)
    )

    return {
        "component": "C3-severity-classification",
        "session_id": session_id,
        "user_id": user_id,
        "primary_disorder": disorder,
        "therapy_focus": THERAPY_FOCUS[disorder],
        "severity_level": level,
        "severity_label": unified_result["severity_label"],
        "risk_level": unified_result["risk_level"],
        "confidence_score": unified_result["confidence_score"],
        "confidence_band": uncertainty_result["confidence_band"],

        "disorder_breakdown": disorder_result["probabilities"],
        "severity_breakdown": severity_result["probabilities"],
        "expected_level": severity_result.get("expected_level"),

        "stuttering_events": stuttering_result["events"],
        "stuttering_positive_events": stuttering_result["positive_events"],

        "stage1_acoustic": adapter_result["stage1_acoustic"],
        "feature_vector": [
            {"feature": n, "label": FEATURE_LABELS[n], "value": round(features[n], 4),
             "imputed": n in adapter_result["missing_fields"]}
            for n in FEATURE_ORDER
        ],
        "feature_importance": {
            "disorder_classifier": disorder_result.get("feature_importance", []),
            "severity_estimator": severity_result.get("feature_importance", []),
        },
        "flagged_sounds": (handoff or {}).get("flagged_sounds", []),

        "uncertainty": {
            "confidence_score": uncertainty_result["confidence_score"],
            "confidence_band": uncertainty_result["confidence_band"],
            "normalised_entropy": uncertainty_result["normalised_entropy"],
            "epistemic_std": uncertainty_result["epistemic_std"],
            "temperature": uncertainty_result["temperature"],
            "method": uncertainty_result["method"],
        },

        "unified_score": {
            "severity_level": unified_result["severity_level"],
            "severity_label": unified_result["severity_label"],
            "risk_level": unified_result["risk_level"],
            "confidence_score": unified_result["confidence_score"],
            "scoring_method": unified_result["scoring_method"],
            "scoring_explanation": unified_result["scoring_explanation"],
            "components_used": unified_result["components_used"],
        },

        "professional_review_recommended": review,
        "recommendations": _recommendations(disorder, level, review),

        "input_summary": {
            "component2_schema": adapter_result["source_schema"],
            "missing_component2_fields": adapter_result["missing_fields"],
            "component2_confidence": adapter_result["component2_confidence"],
        },

        "model_status": {
            "dysarthria_acoustic_torgo": adapter_result["stage1_acoustic"]["status"],
            "disorder_classifier": disorder_result["model_status"],
            "severity_estimator": severity_result["model_status"],
            "stuttering_multilabel": stuttering_result["model_status"],
            "any_untrained_fallback_used": any_fallback,
        },

        "model_version": MODEL_VERSION,
        "disclaimer": (
            "Research screening prototype. The disorder / severity / stuttering models are trained "
            "on a SYNTHETIC DEMO dataset and are NOT clinically validated; only the stage-1 "
            "dysarthria model uses real research data (TORGO). This output is a screening risk "
            "indicator, not a medical diagnosis."
        ),
    }
