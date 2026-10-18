"""
Therapist-controlled parts of the plan (storage-agnostic - the platform passes rows in):

  homework   assigned exercises with a due date and a number of attempts asked for; progress
             counts the patient's attempts since the assignment was made
  goals      measurable targets a therapist sets on top of the automatic goals, measured over
             the last 7 days (average score, exercises per week, long pauses per exercise)
  alerts     plain sentences for the therapist ("hasn't practised for 9 days", "score dropped
             3 times in a row", "the last 3 exercises felt hard", "homework overdue")

The therapist steers the adaptive engine (assigned exercises always come first in the plan)
instead of only watching it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .progress import parse

GOAL_METRICS: dict[str, dict] = {
    "average_score": {"label": "Average score (last 7 days)", "direction": "at_least", "unit": "points"},
    "sessions_per_week": {"label": "Exercises in the last 7 days", "direction": "at_least", "unit": "exercises"},
    "long_pauses_per_exercise": {"label": "Long pauses per exercise (last 7 days)", "direction": "at_most", "unit": "pauses"},
}
INACTIVE_DAYS = 7
SCORE_DROPS = 3  # consecutive drops that raise an alert


def _date(value) -> date | None:
    if value is None or isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def homework_status(items: list[dict], records: list[dict], today: date | None = None,
                    titles: dict[str, dict] | None = None) -> list[dict]:
    """items: [{exercise_id, assigned_at (ISO or None), due (date/ISO or None), times}] -> progress per item."""
    today = today or datetime.now(timezone.utc).date()
    titles = titles or {}
    out = []
    for item in items:
        since = parse(item["assigned_at"]) if item.get("assigned_at") else None
        done_count = sum(1 for r in records if r["exercise_id"] == item["exercise_id"]
                         and (since is None or parse(r["completed_at"]) >= since))
        times = max(1, int(item.get("times") or 1))
        due = _date(item.get("due"))
        done = done_count >= times
        ex = titles.get(item["exercise_id"]) or {}
        out.append({
            "exercise_id": item["exercise_id"],
            "title": ex.get("title", item["exercise_id"]),
            "type": ex.get("type"),
            "assigned_at": item.get("assigned_at"),
            "due": due.isoformat() if due else None,
            "times": times,
            "done_count": min(done_count, times),
            "done": done,
            "overdue": bool(due and not done and today > due),
            "days_left": (due - today).days if due else None,
        })
    return out


def homework_summary(items: list[dict]) -> dict:
    return {"items": items, "open": sum(1 for i in items if not i["done"]), "overdue": sum(1 for i in items if i["overdue"])}


def goal_progress(goals: list[dict], records: list[dict], now: datetime | None = None) -> list[dict]:
    """goals: [{id, metric, target}] -> the plan's goal format (+ source 'therapist', direction)."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    recent = [r for r in records if parse(r["completed_at"]) >= since]
    live = [r for r in recent if r.get("speaking_ratio") is not None]
    values = {
        "average_score": round(sum(r["score"] for r in recent) / len(recent)) if recent else None,
        "sessions_per_week": len(recent),
        "long_pauses_per_exercise": round(sum(r.get("long_pauses", 0) for r in live) / len(live), 1) if live else None,
    }
    out = []
    for g in goals:
        meta = GOAL_METRICS.get(g["metric"])
        if meta is None:
            continue
        current = values[g["metric"]]
        target = float(g["target"])
        if current is None:
            met = False
        elif meta["direction"] == "at_least":
            met = current >= target
        else:
            met = current <= target
        comparator = "≥" if meta["direction"] == "at_least" else "≤"
        out.append({
            "id": f"therapist-{g['id']}", "goal_id": g["id"], "metric": g["metric"],
            "text": f"{meta['label']} {comparator} {target:g}", "label": meta["label"],
            "current": current, "target": target, "unit": meta["unit"], "met": met,
            "direction": meta["direction"], "source": "therapist",
        })
    return out


def alerts(name: str, records: list[dict], homework: list[dict], now: datetime | None = None,
           registered_at: str | None = None, unrated: int = 0) -> list[dict]:
    """Plain-sentence alerts for one patient, most urgent first."""
    now = now or datetime.now(timezone.utc)
    first = (name or "The patient").split()[0]
    out: list[dict] = []

    def add(kind: str, severity: str, text: str, detail: str = "") -> None:
        out.append({"kind": kind, "severity": severity, "text": text, "detail": detail})

    if not records:
        if registered_at:
            days = (now - parse(registered_at)).days
            if days >= 3:
                add("not_started", "medium", f"{first} hasn't started practising yet", f"Account created {days} days ago.")
    else:
        idle = (now - parse(records[-1]["completed_at"])).days
        if idle >= INACTIVE_DAYS:
            add("inactive", "high", f"{first} hasn't practised for {idle} days",
                "A short message or an easier assignment may help.")
        last = [r["score"] for r in records[-(SCORE_DROPS + 1):]]
        if len(last) == SCORE_DROPS + 1 and all(a > b for a, b in zip(last, last[1:])):
            add("score_drop", "high", f"{first}'s score dropped {SCORE_DROPS} times in a row", " → ".join(map(str, last)))
        if len(records) >= 3 and all(r["self_rating"] == "hard" for r in records[-3:]):
            add("hard", "medium", f"The last 3 exercises felt hard for {first}", "Consider an easier plan or a lower level.")
    for item in homework:
        if item["overdue"]:
            add("homework_overdue", "medium", f"{first} hasn't finished “{item['title']}”",
                f"Due {item['due']} · done {item['done_count']} of {item['times']}.")
    if unrated:
        add("rate", "info", f"{unrated} attempt{'s' if unrated != 1 else ''} not rated yet",
            "Rate attempts 1–5 to validate the practice score.")
    order = ["high", "medium", "info"]
    return sorted(out, key=lambda a: order.index(a["severity"]))
