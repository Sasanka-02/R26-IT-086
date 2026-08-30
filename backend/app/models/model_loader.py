"""
Loads Whisper and HuBERT once per process and keeps them cached.
Import `get_whisper_model()` / `get_hubert_model()` anywhere you need
inference — never instantiate the models directly in a request handler.
"""

import logging
import threading

import torch

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_whisper_model = None
_hubert_model = None
_hubert_extractor = None

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        with _lock:
            if _whisper_model is None:
                import whisper  # openai-whisper

                settings = get_settings()
                logger.info(
                    "Loading Whisper model '%s' on %s",
                    settings.whisper_model_size,
                    DEVICE,
                )
                _whisper_model = whisper.load_model(
                    settings.whisper_model_size, device=DEVICE
                )
    return _whisper_model


def get_hubert_model():
    global _hubert_model, _hubert_extractor
    if _hubert_model is None:
        with _lock:
            if _hubert_model is None:
                from transformers import HubertModel, Wav2Vec2FeatureExtractor

                settings = get_settings()
                logger.info("Loading HuBERT model '%s'", settings.hubert_model_name)
                _hubert_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
                    settings.hubert_model_name
                )
                _hubert_model = HubertModel.from_pretrained(
                    settings.hubert_model_name
                ).to(DEVICE)
                _hubert_model.eval()
    return _hubert_model, _hubert_extractor


def preload_all_models() -> dict[str, bool]:
    """Called at FastAPI startup so the first real request isn't slow."""
    status = {"whisper_loaded": False, "hubert_loaded": False}
    try:
        get_whisper_model()
        status["whisper_loaded"] = True
    except Exception:
        logger.exception("Failed to load Whisper model")

    try:
        get_hubert_model()
        status["hubert_loaded"] = True
    except Exception:
        logger.exception("Failed to load HuBERT model")

    return status


def models_ready() -> dict[str, bool]:
    return {
        "whisper_loaded": _whisper_model is not None,
        "hubert_loaded": _hubert_model is not None,
    }
