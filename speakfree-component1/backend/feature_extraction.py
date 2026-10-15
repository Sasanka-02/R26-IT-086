"""
Acoustic & prosodic feature extraction (Librosa)
-----------------------------------------------
Features reviewed with the project's medical advisor:
  • Words Per Minute (WPM)          – overall speaking rate incl. pauses
  • Articulation Rate (syll/sec)    – syllables per second of *speech time only* (pauses excluded)
  • Energy Mean (dB)                – mean frame energy (loudness)
  • RMSE (Root-Mean-Square Energy)  – mean / std of linear RMS (vocal intensity + stability)
  • Zero Crossing Rate (ZCR)        – noisiness / fricative content of the signal
  • Signal-to-Noise Ratio (dB)      – recording quality (speech power vs. background power)
plus pause statistics and pitch (F0) for prosody.
"""
from __future__ import annotations

import re

import numpy as np

from audio_preprocessing import PreprocessResult, energy_vad, to_db

_VOWEL_GROUPS = re.compile(r"[aeiouy]+")


def count_syllables(word: str) -> int:
    """Heuristic English syllable counter (vowel groups, silent-e correction)."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = len(_VOWEL_GROUPS.findall(w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and groups > 1:
        groups -= 1
    return max(1, groups)


def estimate_snr_db(raw_audio: np.ndarray, sr: int) -> float:
    """
    SNR = 10·log10( P_speech / P_noise )
    P_speech = mean power of VAD speech frames, P_noise = mean power of non-speech frames.
    If the recording has no silent frames, the quietest 10 % of frames estimate the noise.
    """
    import librosa

    rms = librosa.feature.rms(y=raw_audio, frame_length=400, hop_length=160)[0]
    power = rms ** 2
    intervals, _ = energy_vad(raw_audio, sr)
    times = np.arange(len(rms)) * 160 / sr
    speech_mask = np.zeros(len(rms), dtype=bool)
    for s, e in intervals:
        speech_mask |= (times >= s) & (times <= e)

    noise = power[~speech_mask]
    speech = power[speech_mask]
    if speech.size == 0:
        return 0.0
    if noise.size < 5:
        noise = np.sort(power)[: max(1, len(power) // 10)]
    snr = 10.0 * np.log10((np.mean(speech) + 1e-12) / (np.mean(noise) + 1e-12))
    return float(np.clip(snr, -10.0, 80.0))


def extract_features(pre: PreprocessResult, words: list[dict], enable_hubert: bool = False,
                     hubert_model: str = "facebook/hubert-base-ls960") -> dict:
    import librosa

    sr = pre.sample_rate
    y = pre.clean_audio if pre.clean_audio.size else pre.raw_audio

    # ---------------- timing / rate ----------------
    analysed_duration = max(y.size / sr, 1e-6)                      # trimmed duration (incl. pauses)
    speech_time = max(pre.speech_duration_sec, 1e-6)                # VAD speech only
    word_count = len(words)
    syllables = sum(count_syllables(w["word"]) for w in words)

    wpm = word_count / (analysed_duration / 60.0)
    articulation_rate = syllables / speech_time                      # syllables / second of speech
    speech_rate_sps = syllables / analysed_duration                  # syllables / second overall

    # ---------------- energy ----------------
    rms = librosa.feature.rms(y=y, frame_length=400, hop_length=160)[0]
    energy_db = to_db(rms)
    voiced = energy_db > (np.max(energy_db) - 45)                    # ignore silent frames for energy stats

    # ---------------- ZCR ----------------
    zcr = librosa.feature.zero_crossing_rate(y, frame_length=400, hop_length=160)[0]

    # ---------------- pitch (prosody) ----------------
    pitch_mean = pitch_std = 0.0
    try:
        f0 = librosa.yin(y, fmin=65, fmax=500, sr=sr, frame_length=1024, hop_length=160)
        n = min(len(f0), len(voiced))
        f0_voiced = f0[:n][voiced[:n]]
        f0_voiced = f0_voiced[(f0_voiced > 65) & (f0_voiced < 500)]
        if f0_voiced.size:
            pitch_mean = float(np.mean(f0_voiced))
            pitch_std = float(np.std(f0_voiced))
    except Exception:
        pass

    # ---------------- pauses ----------------
    pause_durations = [p.duration for p in pre.pauses]
    minutes = analysed_duration / 60.0

    features = {
        "duration_sec": round(pre.original_duration_sec, 3),
        "analysed_duration_sec": round(analysed_duration, 3),
        "speech_duration_sec": round(speech_time, 3),
        "speech_ratio": round(min(1.0, speech_time / analysed_duration), 4),
        "word_count": word_count,
        "syllable_count": syllables,
        "words_per_minute": round(wpm, 2),
        "articulation_rate_syll_per_sec": round(articulation_rate, 3),
        "speech_rate_syll_per_sec": round(speech_rate_sps, 3),
        "energy_mean_db": round(float(np.mean(energy_db[voiced])) if voiced.any() else float(np.mean(energy_db)), 2),
        "rmse_mean": round(float(np.mean(rms)), 5),
        "rmse_std": round(float(np.std(rms)), 5),
        "zcr_mean": round(float(np.mean(zcr)), 5),
        "zcr_std": round(float(np.std(zcr)), 5),
        "snr_db": round(estimate_snr_db(pre.raw_audio, sr), 2),
        "pitch_mean_hz": round(pitch_mean, 2),
        "pitch_std_hz": round(pitch_std, 2),
        "pause_count": len(pause_durations),
        "pause_rate_per_min": round(len(pause_durations) / minutes, 2) if minutes > 0 else 0.0,
        "mean_pause_sec": round(float(np.mean(pause_durations)), 3) if pause_durations else 0.0,
        "longest_pause_sec": round(float(np.max(pause_durations)), 3) if pause_durations else 0.0,
        "total_pause_sec": round(float(np.sum(pause_durations)), 3) if pause_durations else 0.0,
        "noise_floor_db": pre.noise_floor_db,
    }

    if enable_hubert:
        features["hubert_embedding"] = hubert_embedding(y, sr, hubert_model)

    return features


# ----------------------------------------------------------------------------- HuBERT (optional)
_hubert_cache: dict = {}


def hubert_embedding(y: np.ndarray, sr: int, model_name: str) -> list[float] | None:
    """
    Self-supervised 768-d utterance embedding (mean-pooled last hidden state).
    Optional – requires `pip install transformers` and ENABLE_HUBERT=true.
    Used by downstream components as a learned representation; no training is done here.
    """
    try:
        import torch
        from transformers import AutoFeatureExtractor, HubertModel
    except ImportError:
        return None
    if model_name not in _hubert_cache:
        _hubert_cache[model_name] = (
            AutoFeatureExtractor.from_pretrained(model_name),
            HubertModel.from_pretrained(model_name).eval(),
        )
    extractor, model = _hubert_cache[model_name]
    inputs = extractor(y, sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        hidden = model(**inputs).last_hidden_state  # (1, frames, 768)
    return [round(float(v), 5) for v in hidden.mean(dim=1)[0].tolist()]
