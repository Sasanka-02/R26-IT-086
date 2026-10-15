"""
ASR Confidence Scoring Service  (Component 1 – core novelty)
===========================================================

Novelty: the ASR confidence derived from Whisper token log-probabilities is used as an
objective clinical biomarker. Words that Whisper is unsure about (low probability) are
strongly associated with dysfluency, hesitation, prolongation and distortion.

How log-probabilities are obtained
----------------------------------
1. Whisper transcribes the (denoised, edge-trimmed) audio with word timestamps.
2. For every segment we re-run the Whisper decoder in "teacher-forcing" mode on the exact
   token sequence of each word. The decoder's softmax output at each position gives the
   log-probability of the token that was actually recognised:  logprob_i = log P(t_i | audio, t_<i)
3. Those per-token log-probabilities feed Equations 1–3 below.

Equations
---------
  Eq.1  Token-level linear probability   P(t_i)     = exp(logprob_i)
  Eq.2  Word-level confidence            C_word     = (1/k) * Σ_{i=1..k} exp(logprob_i)
  Eq.3  Overall ASR confidence (%)       C_overall  = ((1/N) * Σ_{i=1..N} exp(logprob_i)) * 100

  A word is a dysfluency candidate when C_word < 0.60.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

import numpy as np

DYSFLUENCY_THRESHOLD = 0.60


# =============================================================================
#  Pure mathematical functions (no Whisper dependency -> unit-testable)
# =============================================================================
def token_linear_probability(logprob: float) -> float:
    # -------------------------------------------------------------------------
    # Equation 1: Token-Level Linear Probability
    #
    #       P(t_i) = exp(logprob_i)
    #
    # Whisper returns natural-log probabilities in (-inf, 0]. Exponentiating maps
    # them back to linear probabilities in (0, 1], which are easier to interpret
    # clinically (0.95 = "95 % sure this token was spoken").
    # -------------------------------------------------------------------------
    return float(np.exp(logprob))


def word_confidence(token_logprobs: list[float]) -> float:
    # -------------------------------------------------------------------------
    # Equation 2: Word-Level Confidence Score
    #
    #                    1    k
    #       C_word  =   ---   Σ   exp(logprob_i)
    #                    k   i=1
    #
    # k = number of sub-word (BPE) tokens that make up the word.
    # Averaging linear probabilities (not log-probs) prevents a single very
    # unlikely sub-token from dominating, while still pulling the score down.
    # -------------------------------------------------------------------------
    if not token_logprobs:
        return 0.0
    k = len(token_logprobs)
    return float(np.sum(np.exp(np.asarray(token_logprobs, dtype=np.float64))) / k)


def overall_confidence_percent(all_token_logprobs: list[float]) -> float:
    # -------------------------------------------------------------------------
    # Equation 3: Overall ASR Confidence Score (%)
    #
    #                       1    N
    #       C_overall = (  ---   Σ   exp(logprob_i)  ) × 100
    #                       N   i=1
    #
    # N = total number of recognised tokens in the whole recording.
    # This is the headline "ASR Confidence" biomarker reported to clinicians and
    # passed to Components 2 and 3.
    # -------------------------------------------------------------------------
    if not all_token_logprobs:
        return 0.0
    n = len(all_token_logprobs)
    return float(np.sum(np.exp(np.asarray(all_token_logprobs, dtype=np.float64))) / n * 100.0)


def is_dysfluency_candidate(c_word: float, threshold: float = DYSFLUENCY_THRESHOLD) -> bool:
    # Rule: C_word < 0.60  ->  flag as dysfluency candidate
    return c_word < threshold


def segment_rejection_reason(
    segment: dict,
    n_words: int,
    no_speech_threshold: float = 0.75,
    compression_threshold: float = 2.4,
    max_words_per_sec: float = 8.0,
) -> str | None:
    """
    Hallucination guard, applied to each Whisper segment BEFORE Eq. 1–3 are computed.

    Whisper can "transcribe" non-speech (tones, noise, music) or fall into a decoding loop
    ("T-T-T-T…" ×100). Such text is often decoded with HIGH confidence, which would corrupt
    the confidence biomarker, so those segments are excluded:

      • no_speech_prob ≥ 0.75  → Whisper itself judges the window to contain no speech
                                 (real speech measured ≈ 0.002–0.004, a pure tone ≈ 0.86)
      • compression_ratio > 2.4 AND > 8 words/s → repetition loop: text is highly repetitive
                                 AND faster than humanly possible (fluent speech ≈ 2–4 words/s).
                                 Requiring both keeps genuine stuttered repetitions, which are slow.

    Returns a reason string if the segment must be rejected, otherwise None.
    """
    no_speech = float(segment.get("no_speech_prob", 0.0))
    if no_speech >= no_speech_threshold:
        return f"no_speech_prob {no_speech:.2f} >= {no_speech_threshold}"
    duration = max(float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)), 0.05)
    rate = n_words / duration
    compression = float(segment.get("compression_ratio", 0.0))
    if compression > compression_threshold and rate > max_words_per_sec:
        return f"repetition loop (compression {compression:.1f}, {rate:.0f} words/s)"
    return None


def confidence_level(c_word: float, threshold: float = DYSFLUENCY_THRESHOLD, high: float = 0.90) -> str:
    """Heat-map band used by the dashboard: high (>=0.90), medium (0.60–0.90), low (<0.60)."""
    if c_word >= high:
        return "high"
    if c_word >= threshold:
        return "medium"
    return "low"


# =============================================================================
#  Data containers
# =============================================================================
@dataclass
class TokenScore:
    token: str
    token_id: int
    logprob: float
    probability: float  # Eq. 1

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "token_id": self.token_id,
            "logprob": round(self.logprob, 5),
            "probability": round(self.probability, 5),
        }


@dataclass
class WordScore:
    index: int
    word: str
    start: float
    end: float
    confidence: float                     # Eq. 2
    is_dysfluency_candidate: bool
    level: str
    whisper_word_probability: float
    tokens: list[TokenScore] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "word": self.word,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.end - self.start, 3),
            "confidence": round(self.confidence, 4),
            "confidence_percent": round(self.confidence * 100, 2),
            "is_dysfluency_candidate": self.is_dysfluency_candidate,
            "level": self.level,
            "whisper_word_probability": round(self.whisper_word_probability, 4),
            "tokens": [t.to_dict() for t in self.tokens],
        }


@dataclass
class TranscriptionResult:
    transcript: str
    words: list[WordScore]
    overall_confidence_percent: float     # Eq. 3
    all_token_logprobs: list[float]
    segments: list[dict]
    rejected_segments: list[dict]
    language: str
    model_name: str
    device: str


# =============================================================================
#  Whisper service
# =============================================================================
class WhisperConfidenceASR:
    """Thread-safe, lazily-loaded singleton around openai-whisper."""

    _instance: "WhisperConfidenceASR | None" = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = "base.en", device: str = "auto", verbatim_prompt: str | None = None,
                 threshold: float = DYSFLUENCY_THRESHOLD, no_speech_threshold: float = 0.75, max_words_per_sec: float = 8.0):
        import torch
        import whisper
        from whisper.tokenizer import get_tokenizer

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.model_name = model_name
        self.threshold = threshold
        self.verbatim_prompt = verbatim_prompt
        self.no_speech_threshold = no_speech_threshold
        self.max_words_per_sec = max_words_per_sec
        self._torch = torch
        self._whisper = whisper
        self.model = whisper.load_model(model_name, device=device)
        self.model.eval()
        self.tokenizer = get_tokenizer(
            self.model.is_multilingual,
            num_languages=getattr(self.model, "num_languages", 99),
            language="en",
            task="transcribe",
        )
        self._infer_lock = threading.Lock()  # Whisper models are not re-entrant

    # ------------------------------------------------------------------ singleton
    @classmethod
    def get(cls, model_name: str, device: str, verbatim_prompt: str | None, threshold: float,
            no_speech_threshold: float = 0.75, max_words_per_sec: float = 8.0) -> "WhisperConfidenceASR":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(model_name, device, verbatim_prompt, threshold, no_speech_threshold, max_words_per_sec)
            return cls._instance

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._instance is not None

    # ------------------------------------------------------------------ teacher forcing
    def _token_logprobs(self, segment_audio: np.ndarray, text_tokens: list[int]) -> list[float]:
        """
        Run the decoder once over [SOT…, no_timestamps, text_tokens] and read
        log P(token | audio, previous tokens) for every recognised token.
        """
        whisper, torch = self._whisper, self._torch
        if not text_tokens:
            return []

        mel = whisper.log_mel_spectrogram(
            whisper.pad_or_trim(segment_audio), n_mels=self.model.dims.n_mels
        ).to(self.model.device)

        prefix = [*self.tokenizer.sot_sequence, self.tokenizer.no_timestamps]
        tokens = torch.tensor([prefix + text_tokens], device=self.model.device)

        with torch.no_grad():
            audio_features = self.model.embed_audio(mel.unsqueeze(0))
            logits = self.model.logits(tokens, audio_features)[0]  # (seq_len, vocab)

        # The output at position p predicts token p+1, so the logits that predict
        # text_tokens[0] sit at index len(prefix) - 1. Restrict the vocabulary to text
        # tokens (< EOT) exactly like Whisper's own alignment code does.
        start = len(prefix) - 1
        pred = logits[start: start + len(text_tokens), : self.tokenizer.eot].float()
        log_probs = torch.log_softmax(pred, dim=-1)
        idx = torch.arange(len(text_tokens), device=log_probs.device)
        target = torch.tensor(text_tokens, device=log_probs.device)
        return log_probs[idx, target].cpu().numpy().astype(float).tolist()

    # ------------------------------------------------------------------ main entry
    def transcribe(self, audio: np.ndarray, time_offset: float = 0.0, sample_rate: int = 16000) -> TranscriptionResult:
        with self._infer_lock:
            result = self.model.transcribe(
                audio,
                language="en",
                task="transcribe",
                word_timestamps=True,
                # Greedy decoding first; a segment is re-decoded at a higher temperature ONLY if its
                # text is a repetition loop (gzip compression ratio > 2.4, e.g. "No. No. No. …" ×40).
                # logprob_threshold=None disables Whisper's low-confidence fallback on purpose: low
                # token probabilities are the dysfluency biomarker and must not be "decoded away".
                temperature=(0.0, 0.2, 0.4, 0.6),
                compression_ratio_threshold=2.4,
                logprob_threshold=None,
                no_speech_threshold=None,
                condition_on_previous_text=False,
                initial_prompt=self.verbatim_prompt or None,
                fp16=(self.device == "cuda"),
                verbose=None,
            )

            words: list[WordScore] = []
            all_logprobs: list[float] = []
            segments_out: list[dict] = []
            rejected: list[dict] = []

            for seg in result.get("segments", []):
                seg_words = [w for w in seg.get("words", []) if w.get("word", "").strip()]
                if not seg_words:
                    continue

                reason = segment_rejection_reason(
                    seg, len(seg_words), self.no_speech_threshold, max_words_per_sec=self.max_words_per_sec
                )
                if reason:
                    text = seg.get("text", "").strip()
                    rejected.append({
                        "start": round(float(seg["start"]) + time_offset, 3),
                        "end": round(float(seg["end"]) + time_offset, 3),
                        "text": text[:120] + ("…" if len(text) > 120 else ""),
                        "reason": reason,
                    })
                    continue

                # Sub-word tokens per word (leading space is part of Whisper's BPE token).
                word_token_ids = [self.tokenizer.encode(w["word"]) for w in seg_words]
                flat_tokens = [t for ids in word_token_ids for t in ids]

                # Audio window for this segment (+200 ms tail so the last phone is complete).
                s = max(0, int(seg["start"] * sample_rate))
                e = min(audio.size, int((seg["end"] + 0.2) * sample_rate))
                logprobs = self._token_logprobs(audio[s:e], flat_tokens)
                all_logprobs.extend(logprobs)

                cursor = 0
                for w, ids in zip(seg_words, word_token_ids):
                    lp = logprobs[cursor: cursor + len(ids)]
                    cursor += len(ids)

                    token_scores = [
                        TokenScore(
                            token=self.tokenizer.decode([tid]),
                            token_id=int(tid),
                            logprob=float(l),
                            probability=token_linear_probability(l),  # Eq. 1
                        )
                        for tid, l in zip(ids, lp)
                    ]
                    c_word = word_confidence(lp)  # Eq. 2
                    words.append(
                        WordScore(
                            index=len(words),
                            word=w["word"].strip(),
                            start=float(w["start"]) + time_offset,
                            end=float(w["end"]) + time_offset,
                            confidence=c_word,
                            is_dysfluency_candidate=is_dysfluency_candidate(c_word, self.threshold),
                            level=confidence_level(c_word, self.threshold),
                            whisper_word_probability=float(w.get("probability", 0.0)),
                            tokens=token_scores,
                        )
                    )

                segments_out.append({
                    "id": seg.get("id"),
                    "start": round(float(seg["start"]) + time_offset, 3),
                    "end": round(float(seg["end"]) + time_offset, 3),
                    "text": seg.get("text", "").strip(),
                    "avg_logprob": round(float(seg.get("avg_logprob", 0.0)), 4),
                    "no_speech_prob": round(float(seg.get("no_speech_prob", 0.0)), 4),
                    "compression_ratio": round(float(seg.get("compression_ratio", 0.0)), 3),
                })

        transcript = re.sub(r"\s+", " ", " ".join(w.word for w in words)).strip()
        return TranscriptionResult(
            transcript=transcript,
            words=words,
            overall_confidence_percent=overall_confidence_percent(all_logprobs),  # Eq. 3
            all_token_logprobs=all_logprobs,
            segments=segments_out,
            rejected_segments=rejected,
            language=result.get("language", "en"),
            model_name=self.model_name,
            device=self.device,
        )
