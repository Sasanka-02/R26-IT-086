"""
Component 3 - Multi-Disorder Severity Classification & Risk Prediction
Student: I.L.S. Tharushan (IT21315114)

This package is an isolated module inside the existing Component 2 backend.
It CONSUMES Component 2 output and does not modify or re-run Component 1 or
Component 2 processing.

Public entry point:
    component3.pipeline.run_component3(session_id, user_id, component2_output)
"""

from .common import (
    DISORDER_CLASSES,
    SEVERITY_LEVELS,
    SEVERITY_LABELS,
    STUTTER_EVENTS,
    FEATURE_ORDER,
    MODEL_VERSION,
)

__all__ = [
    "DISORDER_CLASSES",
    "SEVERITY_LEVELS",
    "SEVERITY_LABELS",
    "STUTTER_EVENTS",
    "FEATURE_ORDER",
    "MODEL_VERSION",
]
