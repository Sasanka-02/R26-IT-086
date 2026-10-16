"""Component 1 AnalyzeResponse -> Component 2 articulation score -> Component 3 payload.

The articulation score comes from Component 1's JSON (see articulation_score.py).
If the session recording is also supplied, the phoneme-level PCC-R replaces it,
because PCC-R measures the consonants actually produced.
"""
from datetime import datetime, timezone
from typing import Optional

from services.articulation_score import score_component1

COMPONENT3_SCHEMA_VERSION = "3.1"
PASS_THROUGH_FIELDS = ("analysis_id", "session_id", "patient_id", "age_bracket", "task_type")
PCC_R_FORMULA = "PCC-R = (correct + distorted target consonants) / target consonants x 100"


def build_component3_payload(
    json_score: Optional[dict], pcc: Optional[dict], component1: Optional[dict] = None,
) -> Optional[dict]:
    """The contract Component 3 consumes; None when no score could be produced."""
    if pcc and pcc.get("status") == "scored":
        score = pcc["pcc_r"]
        method, formula, inputs = "pcc_r", PCC_R_FORMULA, pcc.get("counts")
        level, reliability = pcc.get("severity_band"), pcc.get("validity")
        flags = [pcc["gloss_warning"]] if pcc.get("gloss_warning") else []
    elif json_score and json_score.get("status") == "scored":
        score = json_score["articulation_score"]
        method, formula, inputs = json_score["method"], json_score["formula"], json_score["inputs"]
        level, reliability = json_score["articulation_level"], json_score["reliability"]
        flags = json_score["reliability_flags"]
    else:
        return None
    return {
        "schema_version": COMPONENT3_SCHEMA_VERSION,
        "source_component": "Component 2 - Alignment and Articulation Analytics",
        **{key: (component1 or {}).get(key) for key in PASS_THROUGH_FIELDS},
        "articulation_score": score,
        "articulation_level": level,
        "method": method,
        "formula": formula,
        "formula_inputs": inputs,
        "filler_count": (json_score or {}).get("filler_count"),
        "reliability": reliability,
        "reliability_flags": flags,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def process_component1_output(component1: dict, audio_analysis: Optional[dict] = None) -> dict:
    """Score Component 1's JSON; `audio_analysis` is analyze_articulation's output, if any."""
    json_score = score_component1(component1)
    pcc = (audio_analysis or {}).get("articulation_analysis")
    payload = build_component3_payload(json_score, pcc, component1)
    result = {
        "component": "Component 2 - Alignment and Articulation Analytics",
        **{key: component1.get(key) for key in PASS_THROUGH_FIELDS},
        "articulation_score": json_score,
        "score_status": payload["method"] if payload else json_score["status"],
        "ready_for_component3": payload is not None,
        "component3_input": payload,
    }
    if pcc:
        result["pcc_analysis"] = pcc
    if not payload:
        result["message"] = json_score.get("message")
    return result
