"""Audio analysis for SpeakFree Component 2: PCC articulation scoring plus descriptive features."""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import librosa
import numpy as np

from services.pcc_scoring import score_pcc, tokenize_words, word_intelligibility
from services.phoneme_recognition import MODEL_NAME as PHONEME_MODEL_NAME, recognize_phonemes

logger = logging.getLogger(__name__)
GLOSS_WORD_MIN_PROBABILITY = 0.5


@lru_cache(maxsize=2)
def get_whisper_model(model_name="tiny.en"):
    import whisper
    return whisper.load_model(model_name)


def extract_acoustic_features(audio_path: str) -> dict:
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    if y.size == 0 or not np.isfinite(y).all():
        raise ValueError("The uploaded audio could not be decoded or contains invalid samples.")
    duration = float(librosa.get_duration(y=y, sr=sr))
    if duration <= 0:
        raise ValueError("The uploaded audio has no usable duration.")
    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    rms_db = librosa.amplitude_to_db(np.maximum(rms, 1e-10), ref=np.max)
    return {
        "sample_rate_hz": int(sr),
        "duration_seconds": round(duration, 3),
        "mean_rms_energy": round(float(np.mean(rms)), 6) if rms.size else 0.0,
        "rms_energy_std": round(float(np.std(rms)), 6) if rms.size else 0.0,
        "mean_zero_crossing_rate": round(float(np.mean(zcr)), 6) if zcr.size else 0.0,
        "zero_crossing_rate_std": round(float(np.std(zcr)), 6) if zcr.size else 0.0,
        "low_energy_frame_ratio_proxy": round(float(np.mean(rms_db < -35.0)), 4) if rms_db.size else 0.0,
        "feature_status": "descriptive_only",
    }


def transcribe_audio(audio_path: str, model_name="tiny.en") -> dict:
    try:
        model = get_whisper_model(model_name)
        result = model.transcribe(audio_path, language="en", fp16=False, verbose=False,
                                  word_timestamps=True)
        text = (result.get("text") or "").strip()
        segments = result.get("segments") or []
        log_probs = [float(s["avg_logprob"]) for s in segments if s.get("avg_logprob") is not None]
        no_speech = [float(s["no_speech_prob"]) for s in segments if s.get("no_speech_prob") is not None]
        words = [
            {"word": w["word"].strip(), "probability": round(float(w.get("probability", 0.0)), 4)}
            for s in segments for w in (s.get("words") or [])
        ]
        return {
            "status": "available",
            "model": model_name,
            "language": "en",
            "recognized_text": text,
            "recognized_word_count": len(text.split()),
            "words": words,
            "average_log_probability": round(float(np.mean(log_probs)), 4) if log_probs else None,
            "average_no_speech_probability": round(float(np.mean(no_speech)), 4) if no_speech else None,
            "interpretation_note": "ASR metadata is descriptive; not calibrated clinical confidence."
        }
    except Exception:
        logger.exception("Whisper transcription failed")
        return {
            "status": "unavailable",
            "model": model_name,
            "recognized_text": None,
            "recognized_word_count": None,
            "words": [],
            "average_log_probability": None,
            "average_no_speech_probability": None,
            "message": "ASR unavailable. Check Whisper and FFmpeg in the backend terminal."
        }


def gloss_from_whisper(asr: dict) -> tuple[list[str], set[int]]:
    """Intended words from Whisper; words below the probability threshold are left unscored."""
    words, unscored = [], set()
    for w in asr.get("words") or []:
        for token in tokenize_words(w["word"]):
            if w["probability"] < GLOSS_WORD_MIN_PROBABILITY:
                unscored.add(len(words))
            words.append(token)
    if not words:
        words = tokenize_words(asr.get("recognized_text"))
    return words, unscored


def gloss_from_component1(component1: dict) -> tuple[list[str], set[int]]:
    """Intended words from Component 1's word_segments; dysfluency candidates are left unscored."""
    words, unscored = [], set()
    for segment in component1.get("word_segments") or []:
        for token in tokenize_words(segment.get("word")):
            if segment.get("is_dysfluency_candidate"):
                unscored.add(len(words))
            words.append(token)
    if not words:
        words = tokenize_words(component1.get("transcript"))
    return words, unscored


def score_articulation(
    audio_path: str,
    target_text: Optional[str],
    transcript: Optional[str],
    transcript_gloss: tuple[list[str], set[int]],
    transcript_source: str,
) -> dict:
    """PCC from the recording. The gloss is the target text when known, else the transcript."""
    if target_text and tokenize_words(target_text):
        words, unscored, source = tokenize_words(target_text), set(), "target_text"
    else:
        words, unscored = transcript_gloss
        source = transcript_source
    if not words:
        return {"status": "no_gloss",
                "message": "No intended words available: provide the target text or a recording "
                           "with recognisable speech."}
    try:
        produced = recognize_phonemes(audio_path)
    except Exception:
        logger.exception("Phoneme recognition failed")
        return {"status": "phoneme_recognition_unavailable",
                "message": "Phoneme recogniser unavailable. Check the backend terminal "
                           "(transformers / model download)."}
    result = score_pcc(words, produced, unscored, source)
    result["phoneme_model"] = PHONEME_MODEL_NAME
    counts = result["counts"]
    result["gloss_coverage_percent"] = round(100.0 * counts["words_scored"] / counts["words_in_gloss"], 2)
    if source == "target_text":
        result["validity"] = "valid_known_target"
    else:
        result["validity"] = "provisional_transcript_gloss"
        result["gloss_warning"] = (
            f"No target text was given, so the intended words were taken from the transcript. "
            f"Mispronounced words that the ASR transcribes literally or cannot recognise are not "
            f"counted as errors, so PCC may be overestimated. Only {counts['words_scored']} of "
            f"{counts['words_in_gloss']} words could be scored. Provide the target text "
            f"(the words the speaker was asked to say) for a clinically valid PCC."
        )
    if target_text:
        result["word_intelligibility"] = word_intelligibility(target_text, transcript)
    return result


def analyze_articulation(audio_path: str, model_name="tiny.en", target_text: Optional[str] = None,
                         component1: Optional[dict] = None) -> dict:
    acoustic = extract_acoustic_features(audio_path)
    c1 = component1 or {}
    c1_transcript = c1.get("transcript") or " ".join(s.get("word", "") for s in c1.get("word_segments") or [])
    if c1_transcript.strip():
        asr = None
        transcript = c1_transcript
        gloss = gloss_from_component1(component1)
        source = "component1_transcript"
    else:
        asr = transcribe_audio(audio_path, model_name)
        transcript = asr.get("recognized_text")
        gloss = gloss_from_whisper(asr)
        source = "whisper_transcript"
    articulation = score_articulation(audio_path, target_text, transcript, gloss, source)
    return {
        "component": "Component 2 - Alignment and Articulation Analytics",
        "analysis_mode": "phoneme_level_pcc",
        "received_audio_file": Path(audio_path).name,
        "articulation_analysis": articulation,
        "acoustic_articulation_features": acoustic,
        "asr_intelligibility_analysis": asr,
        "score_status": "calculated_automated_pcc" if articulation.get("status") == "scored"
                        else articulation.get("status"),
    }
