"""Articulation score (0-100) from Component 1's AnalyzeResponse (schema 1.x).

Formulas follow "Component 2 Formula Alignment" (SpeakFree R26-IT-086). Every
input is read from Component 1's own fields, so both components share the same
dysfluency threshold (R1), word normalisation (R2) and confidence equations (R3).

Step 1, filler removal: word_segments whose normalised word is in FILLERS are
removed (kept list W). Fillers are dysfluency, reported as filler_count.

Method A, task_type == "reading" and reference_text present:
    WA = 100 x max(0, 1 - (S + D + I) / N)
    N = reference_text words; S, D, I from a word-level Levenshtein alignment of
    reference_text against W. Maier et al. (2009), Speech Communication
    51(5):425-437, DOI 10.1016/j.specom.2008.12.003.

Method B, otherwise (picture, scenario):
    C   = (1/M) x sum of token probabilities over the M tokens of W
          (Component 1 Equation 3 restricted to non-filler words, 0-1 scale)
    CWR = (N - L) / N,  N = |W|,  L = kept words with is_dysfluency_candidate
    Articulation = 100 x (0.5 x C + 0.5 x CWR)
"""
import math
import re
from typing import Optional

FILLERS = frozenset({"um", "uh", "er", "erm", "hmm", "hm", "ah", "mm"})
WORD_RE = re.compile(r"[a-z']+")
SUPPORTED_SCHEMA_MAJOR = "1"
DEFAULT_DYSFLUENCY_THRESHOLD = 0.60
CONFIDENCE_WEIGHT = 0.5
CLEAR_WORD_WEIGHT = 0.5
MIN_RELIABLE_WORDS = 10
MIN_RELIABLE_SNR_DB = 15.0

# Borrowed from the PCC severity bands (Shriberg & Kwiatkowski, 1982); descriptive only.
LEVEL_BANDS = ((85.0, "good"), (65.0, "fair"), (50.0, "poor"), (0.0, "very_poor"))


def normalise_words(text: Optional[str]) -> list[str]:
    """Rule R2: lower-case, keep only letters and apostrophes, split on everything else."""
    return WORD_RE.findall((text or "").lower().replace("’", "'"))


def articulation_level(score: float) -> str:
    for lower, label in LEVEL_BANDS:
        if score >= lower:
            return label
    return "very_poor"


def word_errors(reference: list[str], hypothesis: list[str]) -> dict:
    """Word-level Levenshtein alignment counts: substitutions, deletions, insertions."""
    n, m = len(reference), len(hypothesis)
    d = [[(0, 0, 0, 0)] * (m + 1) for _ in range(n + 1)]  # (cost, S, D, I)
    for i in range(1, n + 1):
        d[i][0] = (i, 0, i, 0)
    for j in range(1, m + 1):
        d[0][j] = (j, 0, 0, j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c, s, dl, ins = d[i - 1][j - 1]
            miss = reference[i - 1] != hypothesis[j - 1]
            diag = (c + miss, s + miss, dl, ins)
            c, s, dl, ins = d[i - 1][j]
            up = (c + 1, s, dl + 1, ins)
            c, s, dl, ins = d[i][j - 1]
            left = (c + 1, s, dl, ins + 1)
            d[i][j] = min(diag, up, left, key=lambda t: t[0])
    _, s, dl, ins = d[n][m]
    return {"substitutions": s, "deletions": dl, "insertions": ins, "correct": n - s - dl}


def _token_probabilities(segment: dict) -> Optional[list[float]]:
    """Component 1 Equation 1: P(t) = exp(logprob), stored as tokens[].probability."""
    tokens = segment.get("tokens")
    if not tokens:
        return None
    probs = []
    for token in tokens:
        if token.get("probability") is not None:
            p = float(token["probability"])
        elif token.get("logprob") is not None:
            p = math.exp(float(token["logprob"]))
        else:
            return None
        if not 0.0 <= p <= 1.0:
            raise ValueError("word_segments[].tokens[].probability must be between 0 and 1.")
        probs.append(p)
    return probs


def _is_flagged(segment: dict, threshold: float) -> bool:
    """Component 1's is_dysfluency_candidate; else Equation 2 (C_word < threshold)."""
    if segment.get("is_dysfluency_candidate") is not None:
        return bool(segment["is_dysfluency_candidate"])
    if segment.get("confidence") is not None:
        return float(segment["confidence"]) < threshold
    probs = _token_probabilities(segment)
    return bool(probs) and sum(probs) / len(probs) < threshold


def split_fillers(component1: dict) -> tuple[list[dict], list[str]]:
    """Step 1: kept segments W (with their normalised words) and the removed fillers."""
    kept, fillers = [], []
    for segment in component1.get("word_segments") or []:
        words = normalise_words(segment.get("word"))
        if not words:
            continue
        if len(words) == 1 and words[0] in FILLERS:
            fillers.append(words[0])
        else:
            kept.append({**segment, "normalised": words})
    return kept, fillers


def _method_a(reference_text: str, kept: list[dict]) -> dict:
    reference = normalise_words(reference_text)
    hypothesis = [w for seg in kept for w in seg["normalised"]]
    errors = word_errors(reference, hypothesis)
    n = len(reference)
    s, d, i = errors["substitutions"], errors["deletions"], errors["insertions"]
    score = 100.0 * max(0.0, 1 - (s + d + i) / n)
    return {
        "method": "A_word_accuracy",
        "formula": "WA = 100 x max(0, 1 - (S + D + I) / N)",
        "articulation_score": round(score, 2),
        "inputs": {"N_reference_words": n, "S": s, "D": d, "I": i,
                   "correct_words": errors["correct"], "reference_text": reference_text,
                   "kept_words": hypothesis},
    }, []


def _method_b(component1: dict, kept: list[dict]) -> tuple[dict, list[str]]:
    flags = []
    threshold = component1.get("dysfluency_threshold")
    threshold = DEFAULT_DYSFLUENCY_THRESHOLD if threshold is None else float(threshold)
    n = len(kept)
    low = sum(_is_flagged(seg, threshold) for seg in kept)
    cwr = (n - low) / n

    per_word = [_token_probabilities(seg) for seg in kept]
    if all(per_word):
        probs = [p for word in per_word for p in word]
        confidence, m, source = sum(probs) / len(probs), len(probs), "eq3_kept_tokens"
    elif component1.get("overall_confidence_percent") is not None:
        confidence = float(component1["overall_confidence_percent"]) / 100.0
        m, source = None, "overall_confidence_percent"
        flags.append("confidence_includes_fillers")
    else:
        confidence, m, source = None, None, None
        flags.append("confidence_missing")

    if confidence is None:
        score = 100.0 * cwr
        formula = "Articulation = 100 x CWR  (no confidence available)"
    else:
        score = 100.0 * (CONFIDENCE_WEIGHT * confidence + CLEAR_WORD_WEIGHT * cwr)
        formula = "Articulation = 100 x (0.5 x C + 0.5 x CWR),  CWR = (N - L) / N"
    return {
        "method": "B_confidence_clear_word_ratio",
        "formula": formula,
        "articulation_score": round(score, 2),
        "inputs": {"N_kept_words": n, "M_kept_tokens": m,
                   "C_confidence": None if confidence is None else round(confidence, 4),
                   "C_source": source, "L_dysfluency_candidates": low,
                   "CWR_clear_word_ratio": round(cwr, 4), "dysfluency_threshold": threshold},
    }, flags


def score_component1(component1: dict) -> dict:
    """Articulation score from Component 1's JSON. status is 'scored' or 'insufficient_data'."""
    kept, fillers = split_fillers(component1)
    reference_text = component1.get("reference_text")
    use_a = component1.get("task_type") == "reading" and bool(normalise_words(reference_text))

    if use_a:
        result, flags = _method_a(reference_text, kept)
    elif kept:
        result, flags = _method_b(component1, kept)
    else:
        return {"status": "insufficient_data", "filler_count": len(fillers),
                "message": "Component 1's JSON has no non-filler word_segments to score."}

    if len(kept) < MIN_RELIABLE_WORDS:
        flags.append("too_few_words")
    snr = (component1.get("acoustic_features") or {}).get("snr_db")
    if snr is not None and float(snr) < MIN_RELIABLE_SNR_DB:
        flags.append("noisy_recording")
    if str(component1.get("schema_version") or "").split(".")[0] != SUPPORTED_SCHEMA_MAJOR:
        flags.append("schema_mismatch")

    score = result["articulation_score"]
    return {
        "status": "scored",
        **result,
        "articulation_level": articulation_level(score),
        "reliability": "reduced" if flags else "normal",
        "reliability_flags": flags,
        "filler_count": len(fillers),
        "fillers_removed": fillers,
    }
