"""
pipeline.py
===========

Orchestrates the full Component 3 flow:

    component2_output
        -> feature_adapter.adapt_features
        -> classifier.classify_disorder
        -> stuttering.analyze_stuttering_events
        -> severity.estimate_severity
        -> uncertainty.estimate_uncertainty
        -> unified_score.compute_unified_score
        -> report.build_report
        -> structured JSON

Component 1 / Component 2 processing is NEVER re-run here.
"""

from __future__ import annotations

import time
import uuid

from .feature_adapter import adapt_features, FeatureAdapterError
from .classifier import classify_disorder
from .stuttering import analyze_stuttering_events
from .severity import estimate_severity
from .uncertainty import estimate_uncertainty, DEFAULT_TEMPERATURE
from .unified_score import compute_unified_score
from .report import build_report
from ._models import get_model_card, models_status


class Component3Error(ValueError):
    """Raised for invalid Component 3 requests."""


def run_component3(
    session_id: str | None,
    user_id: str | None,
    component2_output: dict,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict:
    started = time.time()

    session_id = (session_id or "").strip() or f"c3-{uuid.uuid4().hex[:12]}"
    user_id = (user_id or "").strip() or "anonymous"

    # 1. adapt Component 2 output -> internal feature vector
    try:
        adapter_result = adapt_features(component2_output)
    except FeatureAdapterError as exc:
        raise Component3Error(str(exc)) from exc

    features = adapter_result["features"]
    vector = adapter_result["vector"]

    # 2. multi-disorder classification
    disorder_result = classify_disorder(features, vector)

    # 3. multi-label stuttering events
    stuttering_result = analyze_stuttering_events(features, vector)

    # 4. severity estimation (Level 1-4)
    severity_result = estimate_severity(features, vector)

    # 5. confidence / uncertainty
    uncertainty_result = estimate_uncertainty(disorder_result, temperature=temperature)

    # 6. unified severity score + risk
    unified_result = compute_unified_score(
        disorder_result, severity_result, uncertainty_result, features
    )

    # 7. structured clinical-screening report
    report = build_report(
        session_id=session_id,
        user_id=user_id,
        adapter_result=adapter_result,
        disorder_result=disorder_result,
        stuttering_result=stuttering_result,
        severity_result=severity_result,
        uncertainty_result=uncertainty_result,
        unified_result=unified_result,
        component2_output=(
            component2_output if isinstance(component2_output, dict) else {}
        ),
    )

    report["processing_time_seconds"] = round(time.time() - started, 4)
    return report


def health() -> dict:
    card = get_model_card()
    status = models_status()
    trained = sum(1 for v in status.values() if v)
    return {
        "component": "Component 3 - Multi-Disorder Severity Classification & Risk Prediction",
        "status": "ok",
        "models_trained": f"{trained}/{len(status)}",
        "models": status,
        "model_version": (card or {}).get("model_version", "component3-baseline-v1"),
        "model_card_present": card is not None,
        "note": (
            "If models_trained < 4, run: python Training/component3/train_all.py "
            "(the pipeline still responds using clearly-flagged heuristic "
            "fallbacks until then)."
        ),
    }
