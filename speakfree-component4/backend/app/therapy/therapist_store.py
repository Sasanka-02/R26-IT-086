"""
Therapist-controlled settings per student: assigned exercises, a reading
level override, measurable goals and clinical notes. These feed back into
the adaptive engine, so the therapist steers the system rather than only
watching it.
"""

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

STORE_FILE = Path(__file__).resolve().parents[2] / "data" / "therapist_settings.json"
_lock = threading.Lock()

GOAL_METRICS = {
    "average_score": {"label": "Average score (last 7 days)", "direction": "at_least"},
    "sessions_per_week": {"label": "Exercises in the last 7 days", "direction": "at_least"},
    "long_pauses_per_reading": {"label": "Long pauses per reading (last 7 days)", "direction": "at_most"},
}


def _empty() -> dict:
    return {"assigned": [], "level_override": None, "goals": [], "notes": []}


def _load() -> dict[str, dict]:
    if not STORE_FILE.exists():
        return {}
    try:
        return json.loads(STORE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(STORE_FILE)


def get_settings(student: str) -> dict:
    with _lock:
        return {**_empty(), **_load().get(normalize_user_id(student), {})}


def _update(student: str, mutate) -> dict:
    key = normalize_user_id(student)
    with _lock:
        data = _load()
        settings = {**_empty(), **data.get(key, {})}
        mutate(settings)
        data[key] = settings
        _save(data)
    return settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_assigned(student: str, exercise_ids: list[str], by: str) -> dict:
    def mutate(s):
        s["assigned"] = [{"exercise_id": e, "by": by, "at": _now()} for e in dict.fromkeys(exercise_ids)]
    return _update(student, mutate)


def set_level_override(student: str, level: str | None, by: str) -> dict:
    def mutate(s):
        s["level_override"] = {"level": level, "by": by, "at": _now()} if level else None
    return _update(student, mutate)


def add_goal(student: str, metric: str, target: float, by: str) -> dict:
    def mutate(s):
        s["goals"].append(
            {"id": uuid.uuid4().hex, "metric": metric, "target": target, "by": by, "created_at": _now()}
        )
    return _update(student, mutate)


def remove_goal(student: str, goal_id: str) -> dict:
    def mutate(s):
        s["goals"] = [g for g in s["goals"] if g["id"] != goal_id]
    return _update(student, mutate)


def add_note(student: str, text: str, by: str) -> dict:
    def mutate(s):
        s["notes"].insert(0, {"id": uuid.uuid4().hex, "text": text.strip(), "by": by, "at": _now()})
    return _update(student, mutate)


def goal_progress(goals: list[dict], records: list[dict]) -> list[dict]:
    """Current value of each goal's metric over the last 7 days, and whether it is met."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [r for r in records if datetime.fromisoformat(r["completed_at"]) >= since]
    readings = [r for r in recent if r.get("speaking_ratio") is not None]
    values = {
        "average_score": round(sum(r["score"] for r in recent) / len(recent)) if recent else None,
        "sessions_per_week": len(recent),
        "long_pauses_per_reading": (
            round(sum(r.get("long_pauses", 0) for r in readings) / len(readings), 1) if readings else None
        ),
    }
    out = []
    for g in goals:
        meta = GOAL_METRICS[g["metric"]]
        current = values[g["metric"]]
        if current is None:
            met = False
        elif meta["direction"] == "at_least":
            met = current >= g["target"]
        else:
            met = current <= g["target"]
        comparator = "≥" if meta["direction"] == "at_least" else "≤"
        out.append(
            {
                **g,
                "label": meta["label"],
                "text": f"{meta['label']} {comparator} {g['target']:g}",
                "current": current,
                "met": met,
            }
        )
    return out
