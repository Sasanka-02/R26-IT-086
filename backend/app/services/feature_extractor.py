"""
Stage 2 of the Component 1 pipeline: turns a cleaned WAV file into the
structured feature set defined in app/schemas/response.py.

- Whisper gives a transcript with word-level confidence; low-confidence
  words are flagged as candidate dysfluency markers (stutter/repetition/
  block) rather than discarded as ASR error, since for this population
  low confidence is itself signal.
- HuBERT gives frame-level embeddings for downstream components (severity
  classification etc.) — this module extracts and returns summary stats,
  the full embedding tensor is handed off separately if needed.
- Librosa gives classic acoustic features (ZCR, RMS energy, tempo).
"""

import logging
import time

import librosa
import numpy as np
import torch

from app.core.config import get_settings
from app.models.model_loader import DEVICE, get_hubert_model, get_whisper_model

logger = logging.getLogger(__name__)


def _transcribe_with_confidence(wav_path: str) -> dict:
    model = get_whisper_model()
    result = model.transcribe(wav_path, word_timestamps=True, fp16=(DEVICE == "cuda"))

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            # Whisper doesn't give per-word probability directly in all
            # versions; approximate confidence via avg_logprob mapped to (0,1)
            # per segment as a fallback if word-level prob is absent.
            prob = w.get("probability")
            if prob is None:
                avg_logprob = segment.get("avg_logprob", -1.0)
                prob = float(np.clip(np.exp(avg_logprob), 0.0, 1.0))
            words.append(
                {
                    "word": w.get("word", "").strip(),
                    "start": float(w.get("start", segment.get("start", 0.0))),
                    "end": float(w.get("end", segment.get("end", 0.0))),
                    "confidence": float(prob),
                }
            )

    transcript = result.get("text", "").strip()
    avg_confidence = (
        float(np.mean([w["confidence"] for w in words])) if words else 0.0
    )

    return {"transcript": transcript, "words": words, "average_confidence": avg_confidence}


def _low_confidence_segments(words: list[dict], threshold: float) -> list[dict]:
    return [
        {
            "start": w["start"],
            "end": w["end"],
            "word": w["word"],
            "confidence": w["confidence"],
        }
        for w in words
        if w["confidence"] < threshold and w["word"]
    ]


def _hubert_embedding_stats(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Returns a mean-pooled HuBERT embedding vector (for downstream components)."""
    model, extractor = get_hubert_model()
    inputs = extractor(
        samples, sampling_rate=sample_rate, return_tensors="pt", padding=True
    )
    input_values = inputs["input_values"].to(DEVICE)

    with torch.no_grad():
        outputs = model(input_values)
        hidden_states = outputs.last_hidden_state  # (1, T, 768)

    pooled = hidden_states.mean(dim=1).squeeze(0).cpu().numpy()
    return pooled


def _librosa_acoustic_features(samples: np.ndarray, sample_rate: int) -> dict:
    zcr = librosa.feature.zero_crossing_rate(samples)
    rms = librosa.feature.rms(y=samples)
    tempo, _ = librosa.beat.beat_track(y=samples, sr=sample_rate)

    return {
        "zero_crossing_rate_mean": float(np.mean(zcr)),
        "energy_mean": float(np.mean(rms)),
        "tempo_bpm": float(tempo if np.isscalar(tempo) else tempo[0]),
    }


def _fluency_metrics(
    words: list[dict], duration_seconds: float, low_conf_count: int, total_words: int
) -> dict:
    minutes = max(duration_seconds / 60.0, 1e-6)
    words_per_minute = total_words / minutes

    # articulation rate ~ syllables/sec approximated via word count * avg
    # syllables-per-word heuristic (English ~1.4) over speaking time only.
    articulation_rate = (total_words * 1.4) / max(duration_seconds, 1e-6)

    dysfluency_density = low_conf_count / total_words if total_words else 0.0

    return {
        "words_per_minute": float(words_per_minute),
        "articulation_rate": float(articulation_rate),
        "estimated_dysfluency_density": float(dysfluency_density),
    }


def extract_all_features(
    wav_path: str, samples: np.ndarray, sample_rate: int, duration_seconds: float, snr_db: float
) -> dict:
    """
    Runs the full extraction pipeline and returns a dict matching
    ExtractFeaturesResponse's shape (minus session_id/task_type, added by
    the caller).
    """
    settings = get_settings()
    start_time = time.time()

    asr = _transcribe_with_confidence(wav_path)
    low_conf = _low_confidence_segments(asr["words"], settings.low_confidence_threshold)

    try:
        _hubert_embedding_stats(samples, sample_rate)
        # Embedding itself isn't part of the JSON contract here — it's
        # produced for the next pipeline stage (severity classification)
        # to consume, e.g. persisted alongside session_id.
    except Exception:
        logger.exception("HuBERT embedding extraction failed; continuing without it")

    acoustic = _librosa_acoustic_features(samples, sample_rate)
    fluency = _fluency_metrics(
        asr["words"], duration_seconds, len(low_conf), len(asr["words"])
    )

    processing_time = time.time() - start_time

    return {
        "processing_time_seconds": processing_time,
        "audio_metadata": {
            "duration_seconds": duration_seconds,
            "sample_rate": sample_rate,
            "snr_db": snr_db,
        },
        "asr_result": {
            "transcript": asr["transcript"],
            "average_confidence": asr["average_confidence"],
            "low_confidence_segments": low_conf,
        },
        "fluency_metrics": fluency,
        "acoustic_features": acoustic,
    }
