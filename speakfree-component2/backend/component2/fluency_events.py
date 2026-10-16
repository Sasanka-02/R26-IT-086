"""
Observable fluency events, counted from Component 1's word timings (no audio, no new ASR).

These counts are not part of the articulation score. They are passed to Component 3 as
disfluency indicators (the stuttering-event model needs them):

  filler_count             words in F = {um, uh, er, ...}
  word_repetition_count    the same word said twice in a row   ("the the boy")
  phrase_repetition_count  the same two-word phrase said twice ("the boy the boy")
  prolongation_count       a non-filler word held much longer than its length suggests
                           (duration > max(PROLONG_MIN_SEC, PROLONG_SEC_PER_CHAR x letters))
  long_pause_count         silent gaps >= LONG_PAUSE_SEC inside the speech (blocks / hesitations)
"""
from __future__ import annotations

from .articulation_score import FILLERS, normalise_words

PROLONG_MIN_SEC = 0.9
PROLONG_SEC_PER_CHAR = 0.22
LONG_PAUSE_SEC = 1.0


def _words(component1: dict) -> list[dict]:
    out = []
    for seg in component1.get("word_segments") or []:
        norm = normalise_words(seg.get("word"))
        if norm:
            out.append({"w": " ".join(norm), "start": float(seg.get("start") or 0.0),
                        "end": float(seg.get("end") or 0.0)})
    return out


def count_fluency_events(component1: dict) -> dict:
    words = _words(component1)
    seq = [w["w"] for w in words]

    fillers = sum(1 for w in seq if w in FILLERS)
    content = [w for w in words if w["w"] not in FILLERS]
    content_seq = [w["w"] for w in content]

    word_reps = sum(1 for a, b in zip(content_seq, content_seq[1:]) if a == b)
    phrase_reps = sum(
        1 for i in range(len(content_seq) - 3)
        if content_seq[i:i + 2] == content_seq[i + 2:i + 4] and content_seq[i] != content_seq[i + 1]
    )
    prolongations = [
        w["w"] for w in content
        if (w["end"] - w["start"]) > max(PROLONG_MIN_SEC, PROLONG_SEC_PER_CHAR * len(w["w"]))
    ]
    pauses = [p for p in component1.get("pauses") or [] if float(p.get("duration", 0.0)) >= LONG_PAUSE_SEC]

    return {
        "word_count": len(seq),
        "content_word_count": len(content_seq),
        "filler_count": fillers,
        "word_repetition_count": word_reps,
        "phrase_repetition_count": phrase_reps,
        "prolongation_count": len(prolongations),
        "prolonged_words": prolongations[:10],
        "long_pause_count": len(pauses),
        "longest_pause_sec": round(max((float(p["duration"]) for p in component1.get("pauses") or []), default=0.0), 3),
    }
