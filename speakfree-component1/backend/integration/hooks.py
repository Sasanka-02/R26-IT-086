"""
Hooks Component 1 calls while a recording is still in memory.

Raw audio is never stored, so anything a later component needs from the waveform must be
computed during POST /api/v1/analyze. Today that is Component 3's TORGO acoustic windows
(numeric features only), stored under `model_features.acoustic_biomarker_windows`.
"""
from __future__ import annotations

import logging

from . import COMPONENT_DIRS  # noqa: F401  (sys.path bootstrap)

log = logging.getLogger("speakfree.integration")


def acoustic_biomarker_windows(raw_audio, sample_rate: int, speech_intervals) -> list[dict]:
    """TORGO-compatible feature windows for Component 3; [] if unavailable (never fails the analysis)."""
    try:
        from component3.acoustic_windows import extract_acoustic_windows

        return extract_acoustic_windows(raw_audio, sample_rate, list(speech_intervals))
    except Exception:  # pragma: no cover - optional stage, must never break Component 1
        log.exception("Acoustic biomarker windows failed; Component 3 will impute P(dysarthria)")
        return []


def warmup() -> None:
    """Compile librosa's pYIN (numba JIT, ~20 s once) and load the Component 3 models."""
    import numpy as np

    sr = 16000
    t = np.arange(sr * 2) / sr
    acoustic_biomarker_windows((0.1 * np.sin(2 * np.pi * 150 * t)).astype(np.float32), sr, [(0.5, 1.5)])
    from component3 import _models

    _models.get_dysarthria_real_bundle()
    _models.get_disorder_bundle()
    _models.get_severity_bundle()
    _models.get_stuttering_bundle()
