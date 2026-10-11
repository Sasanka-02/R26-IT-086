"""
Usability evaluation with the System Usability Scale (SUS).

SUS is a standard 10-item questionnaire answered on a 1–5 agreement scale.
Odd items are positively worded, even items negatively worded:

    item score  = (answer − 1)   for odd items
                = (5 − answer)   for even items
    SUS         = 2.5 × Σ item scores          (0–100)

A score of 68 is the commonly used average benchmark. Students are invited
after a few exercises; therapists can respond from the portal. Results are
aggregated (mean, standard deviation, 95% confidence interval, per-item
means) for the evidence page.
"""

import json
import math
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

SURVEY_FILE = Path(__file__).resolve().parents[2] / "data" / "surveys.json"
_lock = threading.Lock()

SESSIONS_BEFORE_INVITE = 3
BENCHMARK = 68

ITEMS = [
    "I think that I would like to use SpeakFree frequently.",
    "I found SpeakFree unnecessarily complex.",
    "I thought SpeakFree was easy to use.",
    "I think that I would need the support of a technical person to be able to use SpeakFree.",
    "I found the various functions in SpeakFree were well integrated.",
    "I thought there was too much inconsistency in SpeakFree.",
    "I would imagine that most people would learn to use SpeakFree very quickly.",
    "I found SpeakFree very cumbersome to use.",
    "I felt very confident using SpeakFree.",
    "I needed to learn a lot of things before I could get going with SpeakFree.",
]

# Adjective bands commonly used to interpret SUS scores.
BANDS = [(85, "Excellent"), (71, "Good"), (51, "OK"), (0, "Poor")]


def sus_score(answers: list[int]) -> float:
    if len(answers) != len(ITEMS) or any(a not in (1, 2, 3, 4, 5) for a in answers):
        raise ValueError("SUS needs 10 answers between 1 and 5")
    contributions = [(a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers)]
    return sum(contributions) * 2.5


def band(score: float) -> str:
    return next(label for cutoff, label in BANDS if score >= cutoff)


def _load() -> list[dict]:
    if not SURVEY_FILE.exists():
        return []
    try:
        return json.loads(SURVEY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(data: list[dict]) -> None:
    SURVEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SURVEY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(SURVEY_FILE)


def has_responded(user_id: str) -> bool:
    uid = normalize_user_id(user_id)
    with _lock:
        return any(r["user_id"] == uid for r in _load())


def submit(user_id: str, role: str, answers: list[int], comment: str | None) -> dict:
    """Stores one response per user (a repeat replaces the earlier one)."""
    score = sus_score(answers)
    uid = normalize_user_id(user_id)
    response = {
        "id": uuid.uuid4().hex,
        "user_id": uid,
        "role": role,
        "answers": answers,
        "score": score,
        "comment": (comment or "").strip() or None,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        data = [r for r in _load() if r["user_id"] != uid]
        data.append(response)
        _save(data)
    return {"score": score, "band": band(score)}


def _stats(scores: list[float]) -> dict:
    n = len(scores)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95": None, "band": None}
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / (n - 1)) if n > 1 else 0.0
    half = 1.96 * sd / math.sqrt(n) if n > 1 else None
    return {
        "n": n,
        "mean": round(mean, 1),
        "sd": round(sd, 1),
        "ci95": [round(mean - half, 1), round(mean + half, 1)] if half is not None else None,
        "band": band(mean),
    }


def summary() -> dict:
    with _lock:
        responses = _load()
    scores = [r["score"] for r in responses]
    by_role = {
        role: _stats([r["score"] for r in responses if r["role"] == role])
        for role in ("student", "therapist")
    }
    items = []
    for i, text in enumerate(ITEMS):
        answers = [r["answers"][i] for r in responses]
        items.append(
            {
                "number": i + 1,
                "text": text,
                "positive": i % 2 == 0,
                "mean_answer": round(sum(answers) / len(answers), 2) if answers else None,
            }
        )
    return {
        "overall": _stats(scores),
        "by_role": by_role,
        "benchmark": BENCHMARK,
        "items": items,
        "comments": [
            {"role": r["role"], "score": r["score"], "comment": r["comment"], "submitted_at": r["submitted_at"]}
            for r in sorted(responses, key=lambda r: r["submitted_at"], reverse=True)
            if r["comment"]
        ],
    }
