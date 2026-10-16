"""
Appointment booking. A therapist publishes open session slots (date, time,
length, in clinic or online); a student books one; either side can cancel,
which frees the slot again. Times are stored in UTC (ISO 8601); the browser
shows them in the viewer's local time.
"""

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

APPOINTMENTS_FILE = Path(__file__).resolve().parents[2] / "data" / "appointments.json"
MODES = ("clinic", "online")
_lock = threading.Lock()


def _load() -> list[dict]:
    if not APPOINTMENTS_FILE.exists():
        return []
    try:
        return json.loads(APPOINTMENTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(data: list[dict]) -> None:
    APPOINTMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPOINTMENTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(APPOINTMENTS_FILE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _upcoming(slots: list[dict]) -> list[dict]:
    """Slots that haven't ended yet, soonest first."""
    now = _now()
    live = [s for s in slots if datetime.fromisoformat(s["start"]) + timedelta(minutes=s["minutes"]) > now]
    return sorted(live, key=lambda s: s["start"])


def create_slot(therapist: str, start: datetime, minutes: int, mode: str, student: str | None = None) -> dict:
    """An open slot, or (with `student`) a session booked straight away."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    if start.tzinfo is None:
        raise ValueError("start must include a timezone")
    if start <= _now():
        raise ValueError("The session must be in the future.")
    slot = {
        "id": uuid.uuid4().hex,
        "therapist": normalize_user_id(therapist),
        "start": start.astimezone(timezone.utc).isoformat(),
        "minutes": minutes,
        "mode": mode,
        "student": normalize_user_id(student) if student else None,
        "booked_at": _now().isoformat() if student else None,
    }
    with _lock:
        data = _load()
        end = start + timedelta(minutes=minutes)
        for s in data:
            if s["therapist"] != slot["therapist"]:
                continue
            s_start = datetime.fromisoformat(s["start"])
            if s_start < end and start < s_start + timedelta(minutes=s["minutes"]):
                raise ValueError("This overlaps another session in your calendar.")
        data.append(slot)
        _save(data)
    return slot


def book(slot_id: str, student: str) -> dict:
    with _lock:
        data = _load()
        slot = next((s for s in data if s["id"] == slot_id), None)
        if slot is None or datetime.fromisoformat(slot["start"]) <= _now():
            raise LookupError("This session is no longer available.")
        if slot["student"]:
            raise ValueError("Someone has just booked this session — please choose another.")
        slot["student"] = normalize_user_id(student)
        slot["booked_at"] = _now().isoformat()
        _save(data)
        return slot


def cancel(slot_id: str, by: str, role: str) -> dict:
    """A student cancels their booking (the slot opens again); a therapist
    can free a booked slot or delete an open one."""
    who = normalize_user_id(by)
    with _lock:
        data = _load()
        slot = next((s for s in data if s["id"] == slot_id), None)
        if slot is None:
            raise LookupError("Session not found.")
        if role == "student":
            if slot["student"] != who:
                raise PermissionError("You can only cancel your own booking.")
            slot["student"] = slot["booked_at"] = None
        elif slot["student"]:
            slot["student"] = slot["booked_at"] = None
        else:
            data.remove(slot)
        _save(data)
        return slot


def for_student(student: str) -> dict:
    who = normalize_user_id(student)
    with _lock:
        upcoming = _upcoming(_load())
    return {
        "booked": [s for s in upcoming if s["student"] == who],
        "open": [s for s in upcoming if s["student"] is None],
    }


def for_therapist(therapist: str | None = None) -> list[dict]:
    """Upcoming sessions (all therapists' unless one is given)."""
    with _lock:
        upcoming = _upcoming(_load())
    return [s for s in upcoming if therapist is None or s["therapist"] == normalize_user_id(therapist)]


def delete_student(student: str) -> None:
    who = normalize_user_id(student)
    with _lock:
        data = _load()
        for s in data:
            if s["student"] == who:
                s["student"] = s["booked_at"] = None
        _save(data)
