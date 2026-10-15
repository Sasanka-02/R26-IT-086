"""
Explainable screening scores built on top of the ASR confidence biomarker.

All scores are 0–100 and every formula is deterministic and documented, so a clinician
can see exactly why a score is what it is. No model training is involved.

  ASR Score (Accuracy %)  = word accuracy vs. the reading passage (1 − WER) × 100
                            (picture / scenario tasks have no reference → C_overall is used)
  Fluency Score           = 100 × [0.50·(1 − dysfluency_ratio) + 0.25·pause_score + 0.25·rate_score]
  Pronunciation Score     = 100 × [0.60·mean(C_word) + 0.40·word_accuracy]   (reading)
                            100 × mean(C_word)                               (other tasks)
  Articulation Score*     = 100 × [0.70·pronunciation + 0.30·articulation_rate_score]
                            *provisional proxy – replaced by Component 2's phoneme-level score
  Overall Speech Score    = 0.30·ASR + 0.30·Fluency + 0.25·Pronunciation + 0.15·Articulation

Age norms below are approximate reference ranges for screening only and should be
calibrated with the clinical supervisor.
"""
from __future__ import annotations

import re

import numpy as np

# Typical ranges per age bracket: (WPM low, WPM high), (articulation syll/sec low, high)
AGE_NORMS: dict[int, dict] = {
    1: {"wpm": (70, 130), "artic": (2.8, 4.2)},
    2: {"wpm": (90, 150), "artic": (3.0, 4.5)},
    3: {"wpm": (110, 165), "artic": (3.3, 4.8)},
    4: {"wpm": (120, 175), "artic": (3.5, 5.0)},
    5: {"wpm": (130, 185), "artic": (3.7, 5.3)},
    6: {"wpm": (135, 190), "artic": (3.8, 5.5)},
    7: {"wpm": (140, 195), "artic": (3.9, 5.7)},
}

# Grapheme patterns used to locate words that contain a target sound.
TARGET_SOUNDS: dict[str, str] = {
    "/s/": r"s|ce|ci|cy",
    "/z/": r"z|(?<=[aeiou])s(?=[aeiou])",
    "/r/": r"r",
    "/l/": r"l",
    "/θ/ (th)": r"th",
    "/ʃ/ (sh)": r"sh|tion",
    "/tʃ/ (ch)": r"ch|tch",
    "/k/": r"k|ck|c(?=[aou])|q",
    "/f/": r"f|ph",
    "/v/": r"v",
}

_WORD_RE = re.compile(r"[a-z']+")


def normalise_words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower().replace("’", "'"))


def word_error_rate(reference: str, hypothesis: str) -> dict:
    """Levenshtein alignment at word level → WER, substitutions, deletions, insertions."""
    ref, hyp = normalise_words(reference), normalise_words(hypothesis)
    n, m = len(ref), len(hyp)
    if n == 0:
        return {"wer": 0.0, "substitutions": 0, "deletions": 0, "insertions": m, "reference_words": 0}
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + cost)
    # backtrack to count error types
    i, j, s, dl, ins = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            s += 0 if ref[i - 1] == hyp[j - 1] else 1
            i, j = i - 1, j - 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            dl += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return {
        "wer": round(float(d[n, m]) / n, 4),
        "substitutions": s,
        "deletions": dl,
        "insertions": ins,
        "reference_words": n,
    }


def range_score(value: float, low: float, high: float, tolerance: float = 0.5) -> float:
    """1.0 inside [low, high]; decreases linearly to 0 at ±tolerance·range outside it."""
    if low <= value <= high:
        return 1.0
    span = (high - low) * tolerance + 1e-9
    distance = low - value if value < low else value - high
    return float(max(0.0, 1.0 - distance / span))


def pause_score(pause_rate_per_min: float, longest_pause_sec: float) -> float:
    """≤ 4 significant pauses/min is typical; ≥ 20/min scores 0. Very long blocks (> 2 s) are penalised."""
    base = 1.0 - (pause_rate_per_min - 4.0) / 16.0
    base = float(np.clip(base, 0.0, 1.0))
    if longest_pause_sec > 2.0:
        base *= max(0.5, 1.0 - (longest_pause_sec - 2.0) / 6.0)
    return base


def keyword_coverage(transcript: str, keywords: list[str]) -> float:
    words = normalise_words(transcript)
    if not keywords:
        return 0.0
    hits = sum(1 for k in keywords if any(w.startswith(k[: max(3, len(k) - 2)]) for w in words))
    return hits / len(keywords)


def low_confidence_regions(words: list[dict], gap: float = 0.6) -> list[dict]:
    """Group consecutive dysfluency-candidate words into timeline regions."""
    regions: list[dict] = []
    for w in words:
        if not w["is_dysfluency_candidate"]:
            continue
        if regions and w["start"] - regions[-1]["end"] <= gap:
            regions[-1]["end"] = w["end"]
            regions[-1]["words"].append(w["word"])
            regions[-1]["min_confidence"] = min(regions[-1]["min_confidence"], w["confidence"])
        else:
            regions.append({"start": w["start"], "end": w["end"], "words": [w["word"]], "min_confidence": w["confidence"]})
    for r in regions:
        r["start"], r["end"] = round(r["start"], 3), round(r["end"], 3)
        r["min_confidence"] = round(r["min_confidence"], 4)
    return regions


def sound_findings(words: list[dict], threshold: float = 0.60, high: float = 0.90) -> list[dict]:
    """
    Grapheme-context confidence per target sound: the mean C_word of all words that
    contain the sound's spelling pattern. A provisional indicator until Component 2's
    forced-alignment phoneme scores are available.
    """
    findings = []
    for label, pattern in TARGET_SOUNDS.items():
        rx = re.compile(pattern)
        matched = [w for w in words if rx.search(w["word"].lower())]
        if not matched:
            continue
        mean_c = float(np.mean([w["confidence"] for w in matched]))
        status = "ok" if mean_c >= high else ("warning" if mean_c >= threshold else "flag")
        findings.append({
            "sound": label,
            "accuracy_percent": round(mean_c * 100, 1),
            "word_count": len(matched),
            "flagged_words": [w["word"] for w in matched if w["confidence"] < threshold][:6],
            "status": status,
        })
    return sorted(findings, key=lambda f: f["accuracy_percent"])


def screening_indicator(overall: float) -> dict:
    """Preliminary indicator aligned with Component 3's 1–4 severity scale (not a diagnosis)."""
    if overall >= 85:
        level, label, risk = 1, "Typical range", "low"
    elif overall >= 70:
        level, label, risk = 2, "Mild concern – monitor", "low-moderate"
    elif overall >= 55:
        level, label, risk = 3, "Moderate concern", "moderate"
    else:
        level, label, risk = 4, "Significant concern – SLP referral advised", "high"
    return {
        "severity_hint": level,
        "label": label,
        "risk": risk,
        "note": "Preliminary screening indicator from Component 1. Final disorder type and severity come from Component 3 and clinical judgement.",
    }


def compute_scores(
    *,
    words: list[dict],
    transcript: str,
    overall_confidence: float,
    features: dict,
    age_bracket: int,
    task_type: str,
    reference_text: str | None,
    keywords: list[str] | None,
    threshold: float = 0.60,
) -> dict:
    norms = AGE_NORMS.get(age_bracket, AGE_NORMS[7])
    n_words = len(words)
    confidences = [w["confidence"] for w in words]
    mean_word_conf = float(np.mean(confidences)) if confidences else 0.0
    n_dysfluent = sum(1 for w in words if w["is_dysfluency_candidate"])
    dysfluency_ratio = n_dysfluent / n_words if n_words else 1.0

    # ---- accuracy (reading task has a reference passage) ----
    wer_info = None
    if task_type == "reading" and reference_text:
        wer_info = word_error_rate(reference_text, transcript)
        word_accuracy = max(0.0, 1.0 - wer_info["wer"])
        asr_score = word_accuracy * 100
    else:
        word_accuracy = None
        asr_score = overall_confidence

    # ---- fluency ----
    r_score = range_score(features["words_per_minute"], *norms["wpm"])
    p_score = pause_score(features["pause_rate_per_min"], features["longest_pause_sec"])
    fluency = 100 * (0.50 * (1 - dysfluency_ratio) + 0.25 * p_score + 0.25 * r_score)

    # ---- pronunciation ----
    if word_accuracy is not None:
        pronunciation = 100 * (0.60 * mean_word_conf + 0.40 * word_accuracy)
    else:
        pronunciation = 100 * mean_word_conf

    # ---- articulation (provisional proxy) ----
    a_rate_score = range_score(features["articulation_rate_syll_per_sec"], *norms["artic"])
    articulation = 100 * (0.70 * pronunciation / 100 + 0.30 * a_rate_score)

    overall = 0.30 * asr_score + 0.30 * fluency + 0.25 * pronunciation + 0.15 * articulation

    coverage = keyword_coverage(transcript, keywords or []) if task_type == "picture" else None

    return {
        "asr_accuracy_percent": round(asr_score, 2),
        "asr_score_basis": "word_accuracy_vs_reference" if word_accuracy is not None else "overall_confidence",
        "fluency_score": round(fluency, 2),
        "pronunciation_score": round(pronunciation, 2),
        "articulation_score": round(articulation, 2),
        "articulation_score_source": "component1_proxy",
        "overall_speech_score": round(overall, 2),
        "mean_word_confidence": round(mean_word_conf, 4),
        "dysfluency_candidate_count": n_dysfluent,
        "dysfluency_ratio": round(dysfluency_ratio, 4),
        "word_accuracy_percent": round(word_accuracy * 100, 2) if word_accuracy is not None else None,
        "wer": wer_info,
        "content_coverage_percent": round(coverage * 100, 1) if coverage is not None else None,
        "score_components": {
            "rate_score": round(r_score, 3),
            "pause_score": round(p_score, 3),
            "articulation_rate_score": round(a_rate_score, 3),
            "age_norms": {"wpm": norms["wpm"], "articulation_syll_per_sec": norms["artic"]},
        },
        "screening_indicator": screening_indicator(overall),
        "phoneme_findings": sound_findings(words, threshold),
        "low_confidence_regions": low_confidence_regions(words),
    }
