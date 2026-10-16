"""
Component 2 session pipeline:  Component 1 session  ->  articulation analysis  ->  Component 3 input.

Input  : the session-level Component 1 summary (SessionSummary) and every per-recording
         Component 1 AnalyzeResponse of that session.
Output : the Component 2 report (stored by the platform, shown on the admin dashboard) whose
         `component3_input` block is the hand-off contract consumed by Component 3.

###########################################################################################
#  ★ COMPONENT 2 NOVELTY - SESSION ARTICULATION SCORE                                     #
#                                                                                         #
#  Every recording r is scored with C2-Eq.1 (reading) or C2-Eq.4 (free speech), then the   #
#  session score pools them, weighted by how many words each recording contributed:        #
#                                                                                         #
#        A_session = Σ_r N_r · A_r  /  Σ_r N_r                            ... (C2-Eq.5)   #
#                                                                                         #
#  N_r = kept (non-filler) words of recording r (reference words for Method A), so a       #
#  three-word answer cannot outweigh a ninety-word picture description. The pooled         #
#  confidence and clear-word ratio are reported the same way:                              #
#        C_session   = Σ_r M_r · C_r / Σ_r M_r       (M_r = kept tokens)                   #
#        CWR_session = Σ_r (N_r − L_r) / Σ_r N_r                                           #
###########################################################################################
"""
from __future__ import annotations

from datetime import datetime, timezone

from .articulation_score import articulation_level, score_component1
from .fluency_events import count_fluency_events

COMPONENT_NAME = "C2-articulation-analytics"
SCHEMA_VERSION = "2.0.0"
COMPONENT3_SCHEMA_VERSION = "4.0"
EVENT_KEYS = ("filler_count", "word_repetition_count", "phrase_repetition_count",
              "prolongation_count", "long_pause_count", "word_count", "content_word_count")


def _weight(score: dict) -> int:
    inputs = score.get("inputs") or {}
    return int(inputs.get("N_kept_words") or inputs.get("N_reference_words") or 0)


def _recording_entry(c1: dict, titles: dict[str, str]) -> dict:
    score = score_component1(c1)
    if score.get("status") == "scored" and score["method"] == "A_word_accuracy":
        # kept_words can be long; the admin dashboard only needs the counts
        score["inputs"] = {k: v for k, v in score["inputs"].items() if k != "kept_words"}
    feats = c1.get("acoustic_features") or {}
    return {
        "analysis_id": c1.get("analysis_id"),
        "task_type": c1.get("task_type"),
        "task_id": c1.get("task_id"),
        "title": titles.get(c1.get("task_id") or "", (c1.get("task_type") or "").title()),
        "transcript": c1.get("transcript", ""),
        "duration_sec": float(feats.get("duration_sec") or 0.0),
        "articulation": score,
        "fluency_events": count_fluency_events(c1),
    }


def _pool(entries: list[dict]) -> dict:
    scored = [e for e in entries if e["articulation"].get("status") == "scored"]
    if not scored:
        return {"status": "insufficient_data", "score": None, "level": None, "scored_recordings": 0,
                "message": "No recording had enough non-filler words to score."}

    weights = [_weight(e["articulation"]) for e in scored]
    scores = [float(e["articulation"]["articulation_score"]) for e in scored]
    total_w = sum(weights)
    # ---------------------------------------------------------------- ★ NOVELTY C2-Eq.5
    # A_session = Σ N_r·A_r / Σ N_r   (falls back to the plain mean if no weights)
    session_score = (sum(w * s for w, s in zip(weights, scores)) / total_w) if total_w else sum(scores) / len(scores)

    # pooled confidence C (token-weighted) and clear-word ratio CWR (word-weighted) for Method B recordings
    b = [e["articulation"]["inputs"] for e in scored if e["articulation"]["method"] == "B_confidence_clear_word_ratio"]
    c_pairs = [(i["M_kept_tokens"] or i["N_kept_words"], i["C_confidence"]) for i in b if i.get("C_confidence") is not None]
    m_total = sum(m for m, _ in c_pairs)
    pooled_c = (sum(m * c for m, c in c_pairs) / m_total) if m_total else None
    n_total = sum(i["N_kept_words"] for i in b)
    pooled_cwr = (sum(i["N_kept_words"] - i["L_dysfluency_candidates"] for i in b) / n_total) if n_total else None

    flags = sorted({f for e in scored for f in e["articulation"]["reliability_flags"]})
    # a session is only "reduced" if most of its words come from reduced-reliability recordings
    reduced_w = sum(w for w, e in zip(weights, scored) if e["articulation"]["reliability"] == "reduced")
    reliability = "reduced" if total_w and reduced_w / total_w > 0.5 else "normal"

    return {
        "status": "scored",
        "score": round(session_score, 2),
        "level": articulation_level(session_score),
        "formula": "A_session = Σ N_r·A_r / Σ N_r",
        "weights": weights,
        "scored_recordings": len(scored),
        "total_weighted_words": total_w,
        "pooled_confidence_C": None if pooled_c is None else round(pooled_c, 4),
        "pooled_clear_word_ratio": None if pooled_cwr is None else round(pooled_cwr, 4),
        "methods": sorted({e["articulation"]["method"] for e in scored}),
        "reliability": reliability,
        "reliability_flags": flags,
        "min_recording_score": round(min(scores), 2),
        "max_recording_score": round(max(scores), 2),
    }


def _events_total(entries: list[dict], speech_sec: float) -> dict:
    totals = {k: sum(int(e["fluency_events"][k]) for e in entries) for k in EVENT_KEYS}
    words = max(totals["content_word_count"], 1)
    minutes = max(speech_sec / 60.0, 1e-6)
    return {
        **totals,
        "longest_pause_sec": max((e["fluency_events"]["longest_pause_sec"] for e in entries), default=0.0),
        "filler_rate": round(totals["filler_count"] / max(totals["word_count"], 1), 4),
        "repetition_rate": round((totals["word_repetition_count"] + totals["phrase_repetition_count"]) / words, 4),
        "prolongation_rate": round(totals["prolongation_count"] / words, 4),
        "long_pauses_per_min": round(totals["long_pause_count"] / minutes, 3) if speech_sec > 0 else 0.0,
    }


def _acoustic_windows(recordings: list[dict]) -> list[dict]:
    """TORGO acoustic windows computed by Component 1 at analysis time (raw audio is never kept)."""
    windows = []
    for r in recordings:
        for w in ((r.get("model_features") or {}).get("acoustic_biomarker_windows") or []):
            windows.append({**w, "analysis_id": r.get("analysis_id"), "task_type": r.get("task_type")})
    return windows


def run_component2(session_summary: dict, recordings: list[dict], task_titles: dict[str, str] | None = None) -> dict:
    """Full Component 2 job for one finalised screening session."""
    titles = task_titles or {}
    entries = [_recording_entry(r, titles) for r in recordings]
    pooled = _pool(entries)
    acoustic = session_summary.get("acoustic_summary") or {}
    events = _events_total(entries, float(acoustic.get("total_speech_sec") or 0.0))
    flagged_sounds = [f for f in session_summary.get("phoneme_findings") or [] if f.get("status") != "ok"]

    component3_input = None
    if pooled["status"] == "scored":
        component3_input = {
            "schema_version": COMPONENT3_SCHEMA_VERSION,
            "source_component": COMPONENT_NAME,
            "session_id": session_summary.get("session_id"),
            "patient_id": session_summary.get("patient_id"),
            "age_bracket": session_summary.get("age_bracket"),
            # ---- Component 2 articulation analytics (★ novelty output) ----
            "articulation_score": pooled["score"],
            "articulation_level": pooled["level"],
            "pooled_confidence_C": pooled["pooled_confidence_C"],
            "pooled_clear_word_ratio": pooled["pooled_clear_word_ratio"],
            "articulation_reliability": pooled["reliability"],
            # ---- fluency events counted by Component 2 ----
            "fluency_events": events,
            # ---- Component 1 session biomarkers passed through unchanged ----
            "component1": {
                "overall_confidence_percent": session_summary.get("overall_confidence_percent"),
                "mean_word_confidence": session_summary.get("mean_word_confidence"),
                "dysfluency_ratio": session_summary.get("dysfluency_ratio"),
                "fluency_score": session_summary.get("fluency_score"),
                "pronunciation_score": session_summary.get("pronunciation_score"),
                "asr_accuracy_percent": session_summary.get("asr_accuracy_percent"),
                "overall_speech_score": session_summary.get("overall_speech_score"),
                "words_per_minute": acoustic.get("words_per_minute"),
                "articulation_rate_syll_per_sec": acoustic.get("articulation_rate_syll_per_sec"),
                "pause_rate_per_min": acoustic.get("pause_rate_per_min"),
                "longest_pause_sec": acoustic.get("longest_pause_sec"),
                "snr_db": acoustic.get("snr_db"),
                "total_speech_sec": acoustic.get("total_speech_sec"),
                "screening_indicator": session_summary.get("screening_indicator"),
            },
            "flagged_sounds": [{"sound": f["sound"], "accuracy_percent": f["accuracy_percent"], "status": f["status"]}
                               for f in flagged_sounds],
            "acoustic_biomarker_windows": _acoustic_windows(recordings),
        }

    return {
        "component": COMPONENT_NAME,
        "schema_version": SCHEMA_VERSION,
        "session_id": session_summary.get("session_id"),
        "patient_id": session_summary.get("patient_id"),
        "age_bracket": session_summary.get("age_bracket"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_articulation": pooled,
        "fluency_events": events,
        "flagged_sounds": flagged_sounds,
        "recordings": entries,
        "ready_for_component3": component3_input is not None,
        "component3_input": component3_input,
    }
