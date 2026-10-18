"""
Voice activity detection: Silero (neural) vs the adaptive energy VAD, the fallback, and the
pre-processing record. The TORGO check runs only when SPEAKFREE_TORGO_DIR points at the dataset's
audio folder (the dataset is never part of the app).
"""
import os

import numpy as np
import pytest

import audio_preprocessing as ap

SR = 16000


def white_noise(seconds: float, level: float = 0.05) -> np.ndarray:
    return np.random.default_rng(1).normal(0, level, int(seconds * SR)).astype(np.float32)


def test_fallback_to_energy_when_silero_is_missing(monkeypatch):
    def missing():
        raise ImportError("silero-vad not installed")

    monkeypatch.setattr(ap, "load_silero", missing)
    _, _, used = ap.detect_speech(white_noise(1.0), SR, "silero")
    assert used == "energy"


def test_energy_backend_is_used_when_selected():
    assert ap.detect_speech(white_noise(1.0), SR, "energy")[2] == "energy"


def test_preprocess_records_the_vad_that_ran():
    pre = ap.preprocess(white_noise(1.5), SR, enable_noise_reduction=False, vad_backend="energy")
    assert pre.vad_backend == "energy"


def test_silero_ignores_pure_noise():
    pytest.importorskip("silero_vad")
    intervals, _ = ap.silero_vad(white_noise(3.0, level=0.2), SR)
    assert intervals == []


@pytest.mark.skipif(not os.getenv("SPEAKFREE_TORGO_DIR"), reason="set SPEAKFREE_TORGO_DIR to the TORGO audio folder")
def test_silero_is_stable_in_noise_on_real_speech():
    """On a TORGO sentence at 0 dB SNR the energy VAD loses the speech; Silero keeps the same span."""
    pytest.importorskip("silero_vad")
    import librosa
    import soundfile as sf

    y, sr = sf.read(os.path.join(os.environ["SPEAKFREE_TORGO_DIR"], "FC01_1_arrayMic_0061.wav"), dtype="float32")
    y = librosa.resample(y if y.ndim == 1 else y.mean(1), orig_sr=sr, target_sr=SR)
    noise = np.random.default_rng(0).normal(0, 1, y.size).astype(np.float32)
    noisy = y + noise * np.sqrt(np.mean(y ** 2) / np.mean(noise ** 2))  # 0 dB SNR
    clean_span = ap.silero_vad(y, SR)[0]
    noisy_span = ap.silero_vad(noisy, SR)[0]
    assert clean_span and noisy_span
    assert abs(noisy_span[0][0] - clean_span[0][0]) < 0.2 and abs(noisy_span[-1][1] - clean_span[-1][1]) < 0.2
