"""
Expert validation of the adaptive learning output.

A therapist looks at the weekly plan the engine generated for a student and
judges it "appropriate", "partly appropriate" or "not appropriate". The plan
is stored exactly as the therapist saw it, so the judgement stays attached to
the output it was about even after the plan changes. The evidence page
reports the share of plans judged appropriate, split by rating source just
like the score validation (demo accounts count as synthetic).
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id
from app.therapy.user_store import is_demo_account

REVIEWS_FILE = Path(__file__).resolve().parents[2] / "data" / "plan_reviews.json"
VERDICTS = {
    "appropriate": "Appropriate",
    "partly": "Partly appropriate",
    "not_appropriate": "Not appropriate",
}
_lock = threading.Lock()


def _load() -> list[dict]:
    if not REVIEWS_FILE.exists():
        return []
    try:
        return json.loads(REVIEWS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(data: list[dict]) -> None:
    REVIEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = REVIEWS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(REVIEWS_FILE)


def _snapshot(plan: dict) -> dict:
    return {
        "level": plan["level"]["label"],
        "context": plan["context"],
        "exercises": [
            {k: ex[k] for k in ("id", "title", "type", "source", "predicted_score", "uncertainty")}
            for ex in plan["exercises"]
        ],
    }


def add_review(student: str, plan: dict, verdict: str, note: str | None, by: str) -> dict:
    if verdict not in VERDICTS:
        raise ValueError("verdict must be one of " + ", ".join(VERDICTS))
    review = {
        "id": uuid.uuid4().hex,
        "student": normalize_user_id(student),
        "verdict": verdict,
        "note": (note or "").strip() or None,
        "by": by,
        "at": datetime.now(timezone.utc).isoformat(),
        "source": "synthetic" if is_demo_account(by) else "clinician",
        "plan": _snapshot(plan),
    }
    with _lock:
        data = _load()
        data.append(review)
        _save(data)
    return review


def reviews_for(student: str) -> list[dict]:
    key = normalize_user_id(student)
    with _lock:
        return [r for r in _load() if r["student"] == key]


def _stats(reviews: list[dict]) -> dict:
    n = len(reviews)
    counts = {v: sum(1 for r in reviews if r["verdict"] == v) for v in VERDICTS}
    return {
        "n": n,
        "students": len({r["student"] for r in reviews}),
        "counts": counts,
        "appropriate_pct": round(100 * counts["appropriate"] / n) if n else None,
        "acceptable_pct": round(100 * (counts["appropriate"] + counts["partly"]) / n) if n else None,
    }


def summary() -> dict:
    with _lock:
        reviews = _load()
    return {
        "labels": VERDICTS,
        "clinician": _stats([r for r in reviews if r["source"] == "clinician"]),
        "synthetic": _stats([r for r in reviews if r["source"] == "synthetic"]),
        "recent": [
            {k: r[k] for k in ("student", "verdict", "note", "at", "source")} | {"level": r["plan"]["level"]}
            for r in reversed(reviews[-10:])
        ],
    }
