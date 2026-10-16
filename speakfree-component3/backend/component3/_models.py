"""
Lazy, cached loaders for the trained Component 3 model bundles.

If a model file is missing the loader returns None and the calling module
falls back to a clearly-labelled transparent heuristic (never a hard-coded
or faked ML result).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from .common import (
    DISORDER_MODEL_PATH,
    SEVERITY_MODEL_PATH,
    STUTTER_MODEL_PATH,
    DYSARTHRIA_REAL_MODEL_PATH,
    MODEL_CARD_PATH,
)


def _load(path):
    if not path.exists():
        return None
    import joblib

    try:
        return joblib.load(path)
    except Exception as exc:  # corrupt / version mismatch -> heuristic fallback
        print(f"[component3] WARNING: could not load {path.name}: {exc!r}")
        return None


@lru_cache(maxsize=1)
def get_disorder_bundle() -> Optional[dict]:
    return _load(DISORDER_MODEL_PATH)


@lru_cache(maxsize=1)
def get_severity_bundle() -> Optional[dict]:
    return _load(SEVERITY_MODEL_PATH)


@lru_cache(maxsize=1)
def get_stuttering_bundle() -> Optional[dict]:
    return _load(STUTTER_MODEL_PATH)


@lru_cache(maxsize=1)
def get_dysarthria_real_bundle() -> Optional[dict]:
    return _load(DYSARTHRIA_REAL_MODEL_PATH)


@lru_cache(maxsize=1)
def get_model_card() -> Optional[dict]:
    if not MODEL_CARD_PATH.exists():
        return None
    import json

    try:
        return json.loads(MODEL_CARD_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def models_status() -> dict:
    return {
        "disorder_classifier": get_disorder_bundle() is not None,
        "severity_estimator": get_severity_bundle() is not None,
        "stuttering_multilabel": get_stuttering_bundle() is not None,
        "dysarthria_real_torgo": get_dysarthria_real_bundle() is not None,
    }


def reset_cache() -> None:
    for fn in (
        get_disorder_bundle,
        get_severity_bundle,
        get_stuttering_bundle,
        get_dysarthria_real_bundle,
        get_model_card,
    ):
        fn.cache_clear()
