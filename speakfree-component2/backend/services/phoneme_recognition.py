"""Phoneme recognition with a wav2vec 2.0 CTC model that outputs IPA phones.

Default model: facebook/wav2vec2-lv-60-espeak-cv-ft (Xu, Baevski & Auli, 2021,
"Simple and Effective Zero-shot Cross-lingual Phoneme Recognition",
arXiv:2109.11680). It is not constrained by an English lexicon, so it reports
what was said rather than the nearest real word, which a word-level ASR such
as Whisper would do.
"""
import os
from functools import lru_cache

import librosa
import numpy as np

MODEL_NAME = os.getenv("SPEAKFREE_PHONEME_MODEL", "facebook/wav2vec2-lv-60-espeak-cv-ft")
SAMPLE_RATE = 16000
MAX_CHUNK_SECONDS = 20.0


@lru_cache(maxsize=1)
def _load_model():
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC, Wav2Vec2PhonemeCTCTokenizer

    tokenizer = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(MODEL_NAME, do_phonemize=False)
    extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME).eval()
    return tokenizer, extractor, model


def _speech_chunks(y: np.ndarray) -> list[np.ndarray]:
    """Split on silences so chunks stay under MAX_CHUNK_SECONDS without cutting words."""
    intervals = librosa.effects.split(y, top_db=40)
    max_len = int(MAX_CHUNK_SECONDS * SAMPLE_RATE)
    chunks, start, end = [], None, None
    for s, e in intervals:
        if start is None:
            start, end = s, e
        elif e - start <= max_len:
            end = e
        else:
            chunks.append(y[start:end])
            start, end = s, e
    if start is not None:
        chunks.append(y[start:end])
    out = []
    for c in chunks:
        out.extend(c[i:i + max_len] for i in range(0, len(c), max_len))
    return [c for c in out if len(c) >= SAMPLE_RATE // 10]


def recognize_phonemes(audio_path: str) -> list[str]:
    import torch

    tokenizer, extractor, model = _load_model()
    y, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    phones: list[str] = []
    for chunk in _speech_chunks(y):
        inputs = extractor(chunk, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.inference_mode():
            logits = model(inputs.input_values).logits
        ids = torch.argmax(logits, dim=-1)
        phones.extend(tokenizer.batch_decode(ids)[0].split())
    return phones
