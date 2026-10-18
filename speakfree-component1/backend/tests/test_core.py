"""
Unit tests for the mathematical core (no Whisper / FastAPI needed).
Run from the backend folder:   python -m pytest -q      (or)   python tests/test_core.py
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asr_service import (  # noqa: E402
    confidence_level,
    is_dysfluency_candidate,
    overall_confidence_percent,
    token_linear_probability,
    word_confidence,
)
from audio_preprocessing import energy_vad, find_pauses  # noqa: E402
from age_brackets import age_from_dob, bracket_for_age  # noqa: E402
from scoring import compute_scores, word_error_rate  # noqa: E402


def test_equation_1_token_probability():
    assert token_linear_probability(0.0) == 1.0
    assert math.isclose(token_linear_probability(math.log(0.25)), 0.25, rel_tol=1e-9)


def test_equation_2_word_confidence():
    # tokens with probabilities 0.9 and 0.5 -> C_word = 0.7
    c = word_confidence([math.log(0.9), math.log(0.5)])
    assert math.isclose(c, 0.7, rel_tol=1e-9)
    assert word_confidence([]) == 0.0


def test_equation_3_overall_confidence():
    lps = [math.log(p) for p in (1.0, 0.8, 0.6, 0.2)]
    assert math.isclose(overall_confidence_percent(lps), 65.0, rel_tol=1e-9)


def test_dysfluency_threshold_and_levels():
    assert is_dysfluency_candidate(0.59)
    assert not is_dysfluency_candidate(0.60)
    assert confidence_level(0.95) == "high"
    assert confidence_level(0.75) == "medium"
    assert confidence_level(0.40) == "low"


def test_age_brackets():
    from datetime import date

    assert age_from_dob(date(2016, 10, 15), today=date(2026, 10, 14)) == 9
    assert bracket_for_age(6) == 1 and bracket_for_age(8) == 2 and bracket_for_age(20) == 7
    assert bracket_for_age(21) == 8 and bracket_for_age(100) == 8  # adults: therapy bracket 8
    assert bracket_for_age(5) is None and bracket_for_age(101) is None and bracket_for_age(None) is None


def test_vad_preserves_significant_pause():
    sr = 16000
    t = np.arange(int(0.6 * sr)) / sr
    tone = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
    silence_short = np.zeros(int(0.1 * sr), np.float32)   # 100 ms -> merged
    silence_long = np.zeros(int(0.8 * sr), np.float32)    # 800 ms -> significant pause
    noise = lambda n: (np.random.default_rng(0).normal(0, 0.001, n)).astype(np.float32)  # noqa: E731
    audio = np.concatenate([noise(8000), tone, silence_short, tone, silence_long, tone, noise(8000)])
    audio = audio + noise(audio.size)
    intervals, _ = energy_vad(audio, sr)
    pauses = find_pauses(intervals, 0.25)
    assert len(intervals) == 2, intervals
    assert len(pauses) == 1 and 0.7 < pauses[0].duration < 0.9


def test_wer():
    r = word_error_rate("the cat sat down", "the cat sat sat down")
    assert r["insertions"] == 1 and math.isclose(r["wer"], 0.25)


def test_compute_scores_shape():
    words = [
        {"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3, "confidence": c, "is_dysfluency_candidate": c < 0.6}
        for i, (w, c) in enumerate([("The", 0.98), ("cat", 0.95), ("s-sat", 0.41), ("down", 0.92)])
    ]
    features = {"words_per_minute": 100, "pause_rate_per_min": 3, "longest_pause_sec": 0.5,
                "articulation_rate_syll_per_sec": 3.5}
    s = compute_scores(words=words, transcript="The cat s-sat down", overall_confidence=81.5, features=features,
                       age_bracket=1, task_type="reading", reference_text="The cat sat down",
                       keywords=None)
    assert 0 <= s["overall_speech_score"] <= 100
    assert s["dysfluency_candidate_count"] == 1
    assert s["low_confidence_regions"][0]["words"] == ["s-sat"]


def test_seed_rows_cover_every_bracket():
    from collections import Counter

    from task_bank import seed_rows

    rows = seed_rows()
    assert len({r["id"] for r in rows}) == len(rows)  # unique task ids
    counts = Counter((r["age_bracket"], r["task_type"]) for r in rows)
    for bracket in range(1, 8):
        # 1 reading + 3 picture + 3 scenario (rotation) + 5 questions (3 shown per session)
        assert [counts[(bracket, t)] for t in ("reading", "picture", "scenario", "questions")] == [1, 3, 3, 5]
    for r in rows:
        assert r["id"].startswith(f"b{r['age_bracket']}-")
        assert r["content_text"] and r["max_seconds"] > 0
        if r["task_type"] in ("picture", "scenario"):
            assert r["visual_json"]["kind"] in ("emoji", "chart")
        if r["task_type"] == "picture":
            assert r["keywords"]


def _fake_result(analysis_id, task_type, task_id, confs, conf_percent, tokens, score):
    words = [
        {"word": f"w{i}", "start": i * 0.5, "end": i * 0.5 + 0.4, "confidence": c,
         "is_dysfluency_candidate": c < 0.6, "level": "high" if c >= 0.9 else ("medium" if c >= 0.6 else "low")}
        for i, c in enumerate(confs)
    ]
    features = {"duration_sec": 10.0, "analysed_duration_sec": 10.0, "speech_duration_sec": 8.0, "words_per_minute": 120,
                "articulation_rate_syll_per_sec": 4.0, "snr_db": 25.0, "pitch_mean_hz": 200.0, "pause_count": 1,
                "longest_pause_sec": 0.4, "total_pause_sec": 0.4, "speech_ratio": 0.8}
    return {
        "analysis_id": analysis_id, "task_type": task_type, "task_id": task_id, "age_bracket": 3,
        "created_at": "2026-10-14T10:00:00+00:00", "transcript": " ".join(w["word"] for w in words),
        "overall_confidence_percent": conf_percent, "model": {"token_count": tokens},
        "overall_speech_score": score, "asr_accuracy_percent": score, "fluency_score": score,
        "pronunciation_score": score, "articulation_score": score,
        "dysfluency_candidate_count": sum(w["is_dysfluency_candidate"] for w in words),
        "dysfluency_ratio": 0.0, "content_coverage_percent": None, "word_segments": words,
        "acoustic_features": features,
        "screening_indicator": {"severity_hint": 1, "label": "x", "risk": "low", "note": ""},
    }


def test_session_summary_pools_tokens_and_weights_by_words():
    from session_summary import summarise_session

    a = _fake_result("a", "picture", "b3-pic-1", [0.95, 0.92, 0.4], conf_percent=80.0, tokens=30, score=90.0)
    b = _fake_result("b", "questions", "b3-q-1", [0.7], conf_percent=50.0, tokens=10, score=50.0)
    s = summarise_session([b, a], session_id="s1", patient_id="SF-1", threshold=0.6)

    # Eq. 3 pooled over all 40 tokens: (80·30 + 50·10) / 40 = 72.5
    assert math.isclose(s["overall_confidence_percent"], 72.5)
    # word-weighted score: (90·3 + 50·1) / 4 = 80
    assert math.isclose(s["overall_speech_score"], 80.0)
    assert s["word_count"] == 4 and s["dysfluency_candidate_count"] == 1
    assert s["confidence_distribution"] == {"high": 2, "medium": 1, "low": 1}
    assert [t["task_type"] for t in s["tasks"]] == ["picture", "questions"]  # canonical task order
    assert s["lowest_confidence_words"][0]["confidence"] == 0.4
    assert s["by_task_type"]["questions"]["recordings"] == 1
    assert s["screening_indicator"]["severity_hint"] == 2


def test_hallucination_guard():
    from asr_service import segment_rejection_reason

    # values measured on real recordings: TTS speech vs. a pure test tone
    speech = {"start": 0.0, "end": 6.0, "no_speech_prob": 0.003, "compression_ratio": 1.4}
    tone = {"start": 0.0, "end": 1.0, "no_speech_prob": 0.86, "compression_ratio": 1.5}
    loop = {"start": 0.0, "end": 1.0, "no_speech_prob": 0.10, "compression_ratio": 17.2}
    stutter = {"start": 0.0, "end": 4.0, "no_speech_prob": 0.02, "compression_ratio": 2.6}  # "b-b-b-ball…", slow

    assert segment_rejection_reason(speech, n_words=22) is None
    assert "no_speech" in segment_rejection_reason(tone, n_words=5)
    assert "repetition loop" in segment_rejection_reason(loop, n_words=112)
    assert segment_rejection_reason(stutter, n_words=12) is None  # 3 words/s – genuine repetitions are kept


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
