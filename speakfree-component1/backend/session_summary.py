"""
Session-level Component 1 output.

A screening session contains several recordings (picture, scenario and one per pre-defined
question). This module merges their per-recording results into ONE explainable summary:

  Pooled ASR confidence  = Eq. 3 over every token of every recording
                         = Σ_r (C_overall_r · N_r) / Σ_r N_r          (N_r = token count of recording r)
  Session scores         = word-count-weighted mean of each recording's score
                           (a 3-word answer should not count as much as a 90-word description)
  Sound-level findings   = recomputed on the pooled word list (more evidence per sound)

Pure functions only – no database or Whisper access – so it is unit-testable.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from scoring import screening_indicator, sound_findings

SCORE_KEYS = ("overall_speech_score", "asr_accuracy_percent", "fluency_score", "pronunciation_score", "articulation_score")
TASK_ORDER = {"reading": 0, "picture": 1, "scenario": 2, "questions": 3}


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    total = float(sum(weights))
    if total <= 0:
        return float(np.mean(values)) if values else 0.0
    return float(sum(v * w for v, w in zip(values, weights)) / total)


def _pooled_confidence(results: list[dict]) -> tuple[float, int]:
    tokens = [max(int(r.get("model", {}).get("token_count", 0)), 0) for r in results]
    confs = [float(r["overall_confidence_percent"]) for r in results]
    if sum(tokens) == 0:
        return (float(np.mean(confs)) if confs else 0.0), 0
    return _weighted_mean(confs, tokens), sum(tokens)


def _task_entry(r: dict, task_titles: dict[str, str]) -> dict:
    f = r["acoustic_features"]
    return {
        "analysis_id": r["analysis_id"],
        "task_type": r["task_type"],
        "task_id": r["task_id"],
        "title": task_titles.get(r["task_id"], r["task_type"].title()),
        "transcript": r["transcript"],
        "overall_confidence_percent": round(float(r["overall_confidence_percent"]), 2),
        "overall_speech_score": r["overall_speech_score"],
        "asr_accuracy_percent": r["asr_accuracy_percent"],
        "fluency_score": r["fluency_score"],
        "pronunciation_score": r["pronunciation_score"],
        "articulation_score": r["articulation_score"],
        "word_count": len(r["word_segments"]),
        "token_count": int(r.get("model", {}).get("token_count", 0)),
        "dysfluency_candidate_count": r["dysfluency_candidate_count"],
        "dysfluency_ratio": r["dysfluency_ratio"],
        "content_coverage_percent": r.get("content_coverage_percent"),
        "duration_sec": f.get("duration_sec", 0.0),
        "words_per_minute": f.get("words_per_minute", 0.0),
        "pause_count": f.get("pause_count", 0),
        "snr_db": f.get("snr_db", 0.0),
        "screening_indicator": r["screening_indicator"],
        "created_at": r["created_at"],
    }


def summarise_session(
    results: list[dict],
    *,
    session_id: str,
    patient_id: str,
    threshold: float = 0.60,
    task_titles: dict[str, str] | None = None,
    schema_version: str = "1.1.0",
) -> dict:
    if not results:
        raise ValueError("A session needs at least one analysed recording")
    task_titles = task_titles or {}
    results = sorted(results, key=lambda r: (TASK_ORDER.get(r["task_type"], 9), r["task_id"], str(r["created_at"])))

    # ---- pooled biomarker (Eq. 3 across all tokens) ----
    pooled_conf, total_tokens = _pooled_confidence(results)

    # ---- word-weighted scores ----
    word_counts = [len(r["word_segments"]) for r in results]
    scores = {k: round(_weighted_mean([float(r[k]) for r in results], word_counts), 2) for k in SCORE_KEYS}

    # ---- pooled word list ----
    all_words: list[dict] = []
    for r in results:
        for w in r["word_segments"]:
            all_words.append({**w, "task_type": r["task_type"], "analysis_id": r["analysis_id"], "task_id": r["task_id"]})
    n_words = len(all_words)
    n_dysfluent = sum(1 for w in all_words if w["is_dysfluency_candidate"])
    distribution = {lvl: sum(1 for w in all_words if w["level"] == lvl) for lvl in ("high", "medium", "low")}
    mean_word_conf = float(np.mean([w["confidence"] for w in all_words])) if all_words else 0.0

    lowest = sorted(all_words, key=lambda w: w["confidence"])[:10]
    lowest_words = [
        {
            "word": w["word"],
            "confidence": round(w["confidence"], 4),
            "task_type": w["task_type"],
            "task_id": w["task_id"],
            "analysis_id": w["analysis_id"],
            "start": w["start"],
            "is_dysfluency_candidate": w["is_dysfluency_candidate"],
        }
        for w in lowest
    ]

    # ---- per task type (questions are grouped together) ----
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        grouped[r["task_type"]].append(r)
    by_task_type = {}
    for ttype, rs in grouped.items():
        conf, toks = _pooled_confidence(rs)
        wc = [len(r["word_segments"]) for r in rs]
        by_task_type[ttype] = {
            "recordings": len(rs),
            "overall_confidence_percent": round(conf, 2),
            "overall_speech_score": round(_weighted_mean([r["overall_speech_score"] for r in rs], wc), 2),
            "word_count": sum(wc),
            "token_count": toks,
            "dysfluency_candidate_count": sum(r["dysfluency_candidate_count"] for r in rs),
        }

    # ---- acoustic features ----
    feats = [r["acoustic_features"] for r in results]
    durations = [float(f.get("analysed_duration_sec") or f.get("duration_sec") or 0.0) for f in feats]

    def wmean(key: str) -> float:
        return round(_weighted_mean([float(f.get(key) or 0.0) for f in feats], durations), 3)

    pitched = [(float(f["pitch_mean_hz"]), d) for f, d in zip(feats, durations) if f.get("pitch_mean_hz")]
    acoustic_summary = {
        "total_duration_sec": round(sum(float(f.get("duration_sec", 0.0)) for f in feats), 2),
        "total_speech_sec": round(sum(float(f.get("speech_duration_sec", 0.0)) for f in feats), 2),
        "words_per_minute": wmean("words_per_minute"),
        "articulation_rate_syll_per_sec": wmean("articulation_rate_syll_per_sec"),
        "energy_mean_db": wmean("energy_mean_db"),
        "rmse_mean": wmean("rmse_mean"),
        "zcr_mean": wmean("zcr_mean"),
        "snr_db": wmean("snr_db"),
        "min_snr_db": round(min(float(f.get("snr_db", 0.0)) for f in feats), 2),
        "pitch_mean_hz": round(_weighted_mean([p for p, _ in pitched], [d for _, d in pitched]), 1) if pitched else 0.0,
        "speech_ratio": wmean("speech_ratio"),
        "pause_count": int(sum(int(f.get("pause_count", 0)) for f in feats)),
        "pause_rate_per_min": wmean("pause_rate_per_min"),
        "longest_pause_sec": round(max(float(f.get("longest_pause_sec", 0.0)) for f in feats), 3),
        "total_pause_sec": round(sum(float(f.get("total_pause_sec", 0.0)) for f in feats), 3),
    }

    indicator = screening_indicator(scores["overall_speech_score"])
    age_bracket = results[0]["age_bracket"]

    return {
        "schema_version": schema_version,
        "component": "C1-speech-screening",
        "summary_type": "session",
        "session_id": session_id,
        "patient_id": patient_id,
        "age_bracket": age_bracket,
        "created_at": max(str(r["created_at"]) for r in results),
        "recording_count": len(results),
        "task_types": sorted(grouped, key=lambda t: TASK_ORDER.get(t, 9)),
        # ---- headline biomarker ----
        "overall_confidence_percent": round(pooled_conf, 2),
        "total_token_count": total_tokens,
        "mean_word_confidence": round(mean_word_conf, 4),
        "dysfluency_threshold": threshold,
        # ---- scores ----
        **scores,
        "score_weighting": "word_count",
        "screening_indicator": indicator,
        # ---- word-level evidence ----
        "word_count": n_words,
        "dysfluency_candidate_count": n_dysfluent,
        "dysfluency_ratio": round(n_dysfluent / n_words, 4) if n_words else 0.0,
        "confidence_distribution": distribution,
        "lowest_confidence_words": lowest_words,
        "phoneme_findings": sound_findings(all_words, threshold),
        # ---- breakdowns ----
        "by_task_type": by_task_type,
        "tasks": [_task_entry(r, task_titles) for r in results],
        "acoustic_summary": acoustic_summary,
    }
