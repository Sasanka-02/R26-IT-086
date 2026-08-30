"""
Stage 1 of the Component 1 pipeline: turn whatever the browser recorded
(webm/opus, mp4, ogg...) into a clean, standardized 16kHz mono WAV, with
ambient noise reduced and non-speech silence trimmed — while deliberately
preserving pauses long enough to represent a stuttering block, since those
are clinically meaningful, not noise.
"""

import logging

import numpy as np
import soundfile as sf
import webrtcvad
from pydub import AudioSegment

try:
    import noisereduce as nr
except ImportError:  # pragma: no cover
    nr = None

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
VAD_FRAME_MS = 30
# Silence longer than this is treated as a possible stuttering block and kept.
MAX_SILENCE_TO_TRIM_MS = 1200


def convert_to_wav(input_path: str, output_path: str) -> str:
    """Convert any supported input container/codec to 16kHz mono WAV."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(TARGET_SAMPLE_RATE).set_channels(1)
    audio.export(output_path, format="wav")
    return output_path


def reduce_noise(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    if nr is None:
        logger.warning("noisereduce not installed — skipping denoising step")
        return samples
    return nr.reduce_noise(y=samples, sr=sample_rate, stationary=False)


def estimate_snr_db(samples: np.ndarray, vad_flags: list[bool]) -> float:
    """Rough SNR estimate: speech-frame RMS vs. silence-frame RMS."""
    if not any(vad_flags) or all(vad_flags):
        return 0.0

    frame_len = int(TARGET_SAMPLE_RATE * VAD_FRAME_MS / 1000)
    speech_energy, noise_energy = [], []
    for i, is_speech in enumerate(vad_flags):
        frame = samples[i * frame_len : (i + 1) * frame_len]
        if frame.size == 0:
            continue
        rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)) + 1e-8)
        (speech_energy if is_speech else noise_energy).append(rms)

    if not speech_energy or not noise_energy:
        return 0.0

    signal = np.mean(speech_energy)
    noise = np.mean(noise_energy)
    return float(20 * np.log10((signal + 1e-8) / (noise + 1e-8)))


def apply_vad_trim(samples_int16: np.ndarray, sample_rate: int) -> tuple[np.ndarray, list[bool], float]:
    """
    Runs WebRTC VAD frame-by-frame. Trims leading/trailing non-speech, but
    keeps interior silences up to MAX_SILENCE_TO_TRIM_MS so long stuttering
    blocks survive into the duration/fluency calculations downstream.
    Returns (trimmed_samples, per_frame_vad_flags, snr_db).
    """
    vad = webrtcvad.Vad(2)  # 0-3, 2 = moderately aggressive
    frame_len = int(sample_rate * VAD_FRAME_MS / 1000)
    n_frames = len(samples_int16) // frame_len

    flags: list[bool] = []
    for i in range(n_frames):
        frame = samples_int16[i * frame_len : (i + 1) * frame_len]
        frame_bytes = frame.tobytes()
        try:
            is_speech = vad.is_speech(frame_bytes, sample_rate)
        except Exception:
            is_speech = True  # fail open — don't destroy data on a VAD error
        flags.append(is_speech)

    snr_db = estimate_snr_db(samples_int16, flags)

    if not any(flags):
        return samples_int16, flags, snr_db

    first_speech = flags.index(True)
    last_speech = len(flags) - 1 - flags[::-1].index(True)

    start_sample = max(0, first_speech * frame_len)
    end_sample = min(len(samples_int16), (last_speech + 1) * frame_len)

    trimmed = samples_int16[start_sample:end_sample]
    return trimmed, flags[first_speech : last_speech + 1], snr_db


def preprocess_audio(raw_path: str, wav_path: str) -> dict:
    """
    Full preprocessing pipeline. Returns a dict with the cleaned samples,
    sample rate, duration, and estimated SNR — ready for feature extraction.
    """
    convert_to_wav(raw_path, wav_path)

    samples, sample_rate = sf.read(wav_path, dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)

    denoised = reduce_noise(samples, sample_rate)

    int16_samples = np.clip(denoised * 32768.0, -32768, 32767).astype(np.int16)
    trimmed_int16, vad_flags, snr_db = apply_vad_trim(int16_samples, sample_rate)

    cleaned_float = trimmed_int16.astype(np.float32) / 32768.0
    sf.write(wav_path, cleaned_float, sample_rate)

    duration_seconds = len(cleaned_float) / float(sample_rate)

    return {
        "wav_path": wav_path,
        "samples": cleaned_float,
        "sample_rate": sample_rate,
        "duration_seconds": duration_seconds,
        "snr_db": snr_db,
    }
