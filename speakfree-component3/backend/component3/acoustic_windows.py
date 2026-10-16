"""
TORGO-compatible acoustic feature windows.

The real-data dysarthria model (training/train_dysarthria_real_torgo.py) was trained on TORGO
utterances: short clips (median ~2.5 s) of speech with some silence around it. Raw audio is
never stored by the platform, so Component 1 calls `extract_acoustic_windows()` while the
recording is still in memory and stores only these numeric features (no audio) in its
AnalyzeResponse (`model_features.acoustic_biomarker_windows`). Component 3 later runs the
TORGO model on them (dysarthria_acoustic.py).

To stay close to the training distribution, each window is a WINDOW_SEC slice that starts
PAD_SEC before a detected speech interval - the same shape as a TORGO clip - and the feature
code below is a line-for-line port of the extractor used to build the TORGO feature table
(librosa RMS / ZCR / spectral / pYIN F0 / 13 MFCC, identical parameters).
"""
from __future__ import annotations

import numpy as np

WINDOW_SEC = 3.0
PAD_SEC = 0.4
MAX_WINDOWS = 3
MIN_SPEECH_SEC = 0.5
SILENCE_THRESHOLD = 0.02


def _features(y: np.ndarray, sr: int) -> dict[str, float]:
    import librosa

    duration = float(librosa.get_duration(y=y, sr=sr))
    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr)
    valid = f0[~np.isnan(f0)]
    voiced = rms >= SILENCE_THRESHOLD
    speech_ratio = float(np.sum(voiced) / len(rms)) if len(rms) else 0.0
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

    out = {
        "duration": duration,
        "mean_rms_energy": float(np.mean(rms)),
        "std_rms_energy": float(np.std(rms)),
        "min_rms_energy": float(np.min(rms)),
        "max_rms_energy": float(np.max(rms)),
        "rms_range": float(np.max(rms) - np.min(rms)),
        "mean_zero_crossing_rate": float(np.mean(zcr)),
        "std_zero_crossing_rate": float(np.std(zcr)),
        "mean_spectral_centroid": float(np.mean(centroid)),
        "mean_spectral_bandwidth": float(np.mean(bandwidth)),
        "mean_spectral_rolloff": float(np.mean(rolloff)),
        "mean_f0_hz": float(np.mean(valid)) if valid.size else 0.0,
        "std_f0_hz": float(np.std(valid)) if valid.size else 0.0,
        "min_f0_hz": float(np.min(valid)) if valid.size else 0.0,
        "max_f0_hz": float(np.max(valid)) if valid.size else 0.0,
        "speech_ratio": speech_ratio,
        "speech_rate_proxy": speech_ratio / duration if duration > 0 else 0.0,
    }
    for i, (m, s) in enumerate(zip(np.mean(mfcc, axis=1), np.std(mfcc, axis=1)), start=1):
        out[f"mfcc_{i}_mean"] = float(m)
        out[f"mfcc_{i}_std"] = float(s)
    return {k: round(v, 6) for k, v in out.items()}


def window_starts(speech_intervals: list[tuple[float, float]], total_sec: float) -> list[float]:
    """Up to MAX_WINDOWS non-overlapping window starts, spread over the recording."""
    candidates = []
    last_end = -1.0
    for start, end in speech_intervals:
        if end - start < MIN_SPEECH_SEC * 0.5:
            continue
        s = max(0.0, start - PAD_SEC)
        if s < last_end:
            continue
        if s + WINDOW_SEC > total_sec:
            s = max(0.0, total_sec - WINDOW_SEC)
            if s < last_end:
                continue
        candidates.append(s)
        last_end = s + WINDOW_SEC
    if len(candidates) <= MAX_WINDOWS:
        return candidates
    idx = np.linspace(0, len(candidates) - 1, MAX_WINDOWS).round().astype(int)
    return [candidates[i] for i in sorted(set(idx.tolist()))]


def extract_acoustic_windows(raw_audio: np.ndarray, sample_rate: int,
                             speech_intervals: list[tuple[float, float]]) -> list[dict]:
    """Numeric TORGO-style features for up to MAX_WINDOWS speech windows (no audio is kept)."""
    total = raw_audio.size / sample_rate if sample_rate else 0.0
    if total < MIN_SPEECH_SEC:
        return []
    windows = []
    for start in window_starts(speech_intervals, total):
        a = int(start * sample_rate)
        b = min(raw_audio.size, int((start + WINDOW_SEC) * sample_rate))
        y = np.asarray(raw_audio[a:b], dtype=np.float32)
        if y.size < MIN_SPEECH_SEC * sample_rate:
            continue
        windows.append({"start_sec": round(start, 2), "features": _features(y, sample_rate)})
    return windows
