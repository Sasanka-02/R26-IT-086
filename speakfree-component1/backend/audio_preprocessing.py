"""
Audio ingestion & pre-processing
--------------------------------
1. Decode any browser upload (.webm/opus, .wav, .ogg, .m4a) to 16 kHz mono float32 via FFmpeg.
2. Spectral-gating noise reduction (noisereduce) – optional, configurable.
3. Energy-based Voice Activity Detection (VAD).
4. Silence trimming that ONLY removes leading/trailing silence.
   Internal pauses are preserved exactly, because pauses > 250 ms are
   clinically significant hesitation markers.

All timestamps produced here are on the ORIGINAL recording timeline so the
frontend can scrub the user's own local audio blob.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

import numpy as np

SAMPLE_RATE = 16000
FRAME_MS = 25
HOP_MS = 10
MICRO_GAP_SEC = 0.25        # gaps shorter than this are normal co-articulation, merged into speech
MIN_SPEECH_SEC = 0.08       # ignore speech blips shorter than this (clicks, pops)
EDGE_PADDING_SEC = 0.15     # keep a little audio around the speech when trimming edges


class AudioDecodeError(RuntimeError):
    pass


@dataclass
class Pause:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)

    def to_dict(self) -> dict:
        return {"start": round(self.start, 3), "end": round(self.end, 3), "duration": self.duration}


@dataclass
class PreprocessResult:
    raw_audio: np.ndarray                 # decoded original (for SNR + waveform)
    clean_audio: np.ndarray               # denoised + edge-trimmed (sent to Whisper)
    sample_rate: int
    trim_offset_sec: float                # add to Whisper timestamps -> original timeline
    original_duration_sec: float
    speech_intervals: list[tuple[float, float]]  # original timeline
    pauses: list[Pause] = field(default_factory=list)  # significant internal pauses (>= 250 ms)
    noise_reduction_applied: bool = False
    noise_floor_db: float = -80.0

    @property
    def speech_duration_sec(self) -> float:
        return float(sum(end - start for start, end in self.speech_intervals))


# --------------------------------------------------------------------------- decoding
def decode_audio(path: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Decode with FFmpeg into mono float32 in [-1, 1]. FFmpeg must be on PATH."""
    cmd = [
        "ffmpeg", "-nostdin", "-threads", "0", "-i", path,
        "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sample_rate), "-",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, check=True).stdout
    except FileNotFoundError as exc:
        raise AudioDecodeError("FFmpeg is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise AudioDecodeError(f"Could not decode audio: {exc.stderr.decode(errors='ignore')[-300:]}") from exc
    audio = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
    if audio.size == 0:
        raise AudioDecodeError("The uploaded audio is empty.")
    return audio


# --------------------------------------------------------------------------- framing helpers
def frame_rms(audio: np.ndarray, sr: int = SAMPLE_RATE, frame_ms: int = FRAME_MS, hop_ms: int = HOP_MS) -> np.ndarray:
    frame = int(sr * frame_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    if audio.size < frame:
        audio = np.pad(audio, (0, frame - audio.size))
    n_frames = 1 + (audio.size - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = audio[idx]
    return np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)


def to_db(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-10))


# --------------------------------------------------------------------------- VAD
def energy_vad(audio: np.ndarray, sr: int = SAMPLE_RATE) -> tuple[list[tuple[float, float]], float]:
    """
    Adaptive energy VAD.
    threshold_dB = max(noise_floor + 12 dB, peak - 45 dB)
    noise_floor  = 10th percentile of frame energy (robust to speech-heavy recordings)
    Returns (speech_intervals_in_seconds, noise_floor_db).
    """
    rms_db = to_db(frame_rms(audio, sr))
    noise_floor = float(np.percentile(rms_db, 10))
    peak = float(np.percentile(rms_db, 99))
    threshold = max(noise_floor + 12.0, peak - 45.0)
    voiced = rms_db > threshold

    hop_sec = HOP_MS / 1000
    frame_sec = FRAME_MS / 1000
    intervals: list[tuple[float, float]] = []
    start = None
    for i, is_voiced in enumerate(voiced):
        if is_voiced and start is None:
            start = i * hop_sec
        elif not is_voiced and start is not None:
            intervals.append((start, i * hop_sec + frame_sec))
            start = None
    if start is not None:
        intervals.append((start, len(voiced) * hop_sec + frame_sec))

    duration = audio.size / sr
    intervals = [(max(0.0, s), min(duration, e)) for s, e in intervals]
    return merge_intervals(intervals), noise_floor


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge micro-gaps (< 250 ms) and drop tiny blips. Gaps >= 250 ms are kept as pauses."""
    if not intervals:
        return []
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s - merged[-1][1] < MICRO_GAP_SEC:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(round(s, 3), round(e, 3)) for s, e in merged if e - s >= MIN_SPEECH_SEC]


def find_pauses(intervals: list[tuple[float, float]], min_pause_sec: float) -> list[Pause]:
    """Internal silences between speech intervals that are >= min_pause_sec (clinically significant)."""
    pauses = []
    for (_, prev_end), (next_start, _) in zip(intervals, intervals[1:]):
        if next_start - prev_end >= min_pause_sec:
            pauses.append(Pause(prev_end, next_start))
    return pauses


# --------------------------------------------------------------------------- noise reduction
def reduce_noise(audio: np.ndarray, sr: int) -> tuple[np.ndarray, bool]:
    try:
        import noisereduce as nr  # lazy import – optional dependency
    except ImportError:
        return audio, False
    try:
        cleaned = nr.reduce_noise(y=audio, sr=sr, stationary=True, prop_decrease=0.75)
        return cleaned.astype(np.float32), True
    except Exception:  # never fail the screening because of denoising
        return audio, False


# --------------------------------------------------------------------------- full pipeline
def preprocess(
    raw_audio: np.ndarray,
    sr: int = SAMPLE_RATE,
    enable_noise_reduction: bool = True,
    significant_pause_sec: float = 0.25,
) -> PreprocessResult:
    duration = raw_audio.size / sr

    # Peak-normalise quiet recordings so VAD + Whisper see a consistent level.
    peak = float(np.max(np.abs(raw_audio))) if raw_audio.size else 0.0
    work = raw_audio / peak * 0.95 if 0 < peak < 0.5 else raw_audio.copy()

    nr_applied = False
    if enable_noise_reduction:
        work, nr_applied = reduce_noise(work, sr)

    intervals, noise_floor = energy_vad(work, sr)
    pauses = find_pauses(intervals, significant_pause_sec)

    if intervals:
        trim_start = max(0.0, intervals[0][0] - EDGE_PADDING_SEC)
        trim_end = min(duration, intervals[-1][1] + EDGE_PADDING_SEC)
    else:
        trim_start, trim_end = 0.0, duration

    clean = work[int(trim_start * sr): int(trim_end * sr)].astype(np.float32)

    return PreprocessResult(
        raw_audio=raw_audio,
        clean_audio=clean,
        sample_rate=sr,
        trim_offset_sec=round(trim_start, 3),
        original_duration_sec=round(duration, 3),
        speech_intervals=intervals,
        pauses=pauses,
        noise_reduction_applied=nr_applied,
        noise_floor_db=round(noise_floor, 2),
    )


def waveform_peaks(audio: np.ndarray, buckets: int = 800) -> list[float]:
    """Down-sampled absolute peaks (0–1) for drawing the waveform in the dashboard."""
    if audio.size == 0:
        return []
    buckets = min(buckets, audio.size)
    chunks = np.array_split(np.abs(audio), buckets)
    peaks = np.array([c.max() if c.size else 0.0 for c in chunks])
    top = peaks.max() or 1.0
    return [round(float(p / top), 4) for p in peaks]
