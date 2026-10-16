"""
report.py
=========

Assembles the structured clinical-screening report (the Component 3 public
output contract).

NOT a clinical diagnosis - a research screening result.
"""

from __future__ import annotations

from .common import MODEL_VERSION


def _recommendations(disorder: str, level: int, review: bool) -> list[str]:
    recs: list[str] = []
    if review:
        recs.append(
            "Confidence is limited - recommend review by a qualified "
            "speech-language pathologist before any conclusion."
        )
    if disorder == "normal" and level <= 2:
        recs.append("No screening indicators of a speech disorder detected.")
    if disorder == "stuttering":
        recs.append(
            "Screening indicators consistent with disfluency / stuttering; "
            "consider a fluency-focused assessment."
        )
        if level >= 3:
            recs.append("Consider pacing / gentle-onset therapy support (Component 4).")
    if disorder == "dysarthria":
        recs.append(
            "Screening indicators consistent with dysarthria; consider a "
            "motor-speech assessment."
        )
        if level >= 3:
            recs.append("Consider intelligibility-focused therapy planning (Component 4).")
    if disorder == "articulation":
        recs.append(
            "Screening indicators consistent with an articulation difficulty; "
            "consider a phonological / articulation assessment."
        )
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

    # articulation metrics: pass through the real Component 2 numbers we used
    features = adapter_result["features"]
    articulation_metrics = {
        "overall_articulation_indicator": features["overall_articulation_indicator"],
        "phoneme_consistency": features["phoneme_consistency"],
        "timing_consistency": features["timing_consistency"],
        "duration_variation": features["duration_variation"],
        "acoustic_model_component": features["acoustic_model_component"],
        "alignment_reliability": features["alignment_reliability"],
        "source": "Component 2 alignment & articulation analytics",
        "mfa_alignment_present": bool(
            "alignment_uncertain" not in adapter_result["missing_fields"]
            and features["alignment_uncertain"] == 0.0
        ),
    }

    any_fallback = any(
        r.get("model_status", "").startswith("NOT_TRAINED")
        for r in (disorder_result, severity_result, stuttering_result)
    )

    return {
        "session_id": session_id,
        "user_id": user_id,
        "primary_disorder": disorder,
        "severity_level": level,
        "severity_label": unified_result["severity_label"],
        "risk_level": unified_result["risk_level"],
        "confidence_score": unified_result["confidence_score"],
        "confidence_band": uncertainty_result["confidence_band"],

        "disorder_breakdown": disorder_result["probabilities"],
        "severity_breakdown": severity_result["probabilities"],

        "stuttering_events": stuttering_result["events"],
        "stuttering_positive_events": stuttering_result["positive_events"],

        "articulation_metrics": articulation_metrics,

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
        },

        "professional_review_recommended": review,
        "recommendations": _recommendations(disorder, level, review),

        "input_summary": {
            "component2_source_shape": adapter_result["source_shape"],
            "missing_component2_fields": adapter_result["missing_fields"],
            "component2_confidence": adapter_result["component2_confidence"],
            "component2_clinical_note": (
                component2_output.get("clinical_note")
                if isinstance(component2_output, dict)
                else None
            ),
        },

        "model_status": {
            "disorder_classifier": disorder_result["model_status"],
            "severity_estimator": severity_result["model_status"],
            "stuttering_multilabel": stuttering_result["model_status"],
            "any_untrained_fallback_used": any_fallback,
        },

        "model_version": MODEL_VERSION,
        "disclaimer": (
            "Research screening prototype. Disorder / severity / stuttering "
            "models are trained on a SYNTHETIC DEMO dataset and are NOT "
            "clinically validated. This output is a screening risk indicator, "
            "not a medical diagnosis."
        ),
    }
