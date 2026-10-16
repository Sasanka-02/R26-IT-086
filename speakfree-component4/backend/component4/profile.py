"""
Therapy profile - the Component 3 -> Component 4 hand-off.

build_profile() turns one screening's Component 1 summary, Component 2 report and Component 3
severity report into the profile that drives the adaptive plan. A new screening creates a new
profile (the plan re-anchors on it); attempts are kept across profiles.
"""
from __future__ import annotations

from .categories import FOCI, START_LEVEL_BY_SEVERITY, focus_for, focus_probabilities


def _target_metric(focus: str, c1: dict, c2: dict, flagged: list[dict]) -> dict | None:
    if focus == "fluency" and c1.get("fluency_score") is not None:
        cur = round(float(c1["fluency_score"]))
        return {"text": f"Raise your fluency score from {cur} to {min(100, cur + 10)}", "current": cur,
                "target": min(100, cur + 10), "metric": "c1.fluency_score"}
    art = (c2.get("session_articulation") or {}).get("score")
    if focus == "motor_speech" and art is not None:
        cur = round(float(art))
        return {"text": f"Raise your speech clarity score from {cur} to {min(100, cur + 10)}", "current": cur,
                "target": min(100, cur + 10), "metric": "c2.articulation_score"}
    if focus == "speech_sounds" and flagged:
        worst = flagged[0]
        cur = round(float(worst["accuracy_percent"]))
        return {"text": f"Make the {worst['sound']} sound clearer: {cur}% -> 90%", "current": cur, "target": 90,
                "metric": f"c1.sound:{worst['sound']}"}
    if c1.get("overall_speech_score") is not None:
        cur = round(float(c1["overall_speech_score"]))
        return {"text": f"Keep your overall speech score at {max(cur, 85)}+", "current": cur,
                "target": max(cur, 85), "metric": "c1.overall_speech_score"}
    return None


def build_profile(c3: dict, c1_summary: dict, c2: dict, *, created_at: str, session_id: str) -> dict:
    focus = focus_for(c3.get("primary_disorder"))
    severity = int(c3.get("severity_level") or 1)
    flagged = sorted(c3.get("flagged_sounds") or [], key=lambda f: f.get("accuracy_percent", 100))
    return {
        "focus": focus,
        "focus_name": FOCI[focus]["patient_name"],
        "c3_disorder": c3.get("primary_disorder"),
        "severity_level": severity,
        "severity_label": c3.get("severity_label"),
        "risk_level": c3.get("risk_level"),
        "confidence": float(c3.get("confidence_score") or 0.5),
        "focus_probabilities": focus_probabilities(c3.get("disorder_breakdown"), focus),
        "flagged_sounds": [f["sound"] for f in flagged],
        "stuttering_events": c3.get("stuttering_positive_events") or [],
        "professional_review_recommended": bool(c3.get("professional_review_recommended")),
        "start_level": START_LEVEL_BY_SEVERITY.get(severity, "beginner"),
        "created_at": created_at,
        "source_session_id": session_id,
        "baseline": {
            "fluency_score": c1_summary.get("fluency_score"),
            "overall_speech_score": c1_summary.get("overall_speech_score"),
            "asr_confidence": c1_summary.get("overall_confidence_percent"),
            "articulation_score": (c2.get("session_articulation") or {}).get("score"),
            "target_metric": _target_metric(focus, c1_summary, c2, flagged),
        },
    }
