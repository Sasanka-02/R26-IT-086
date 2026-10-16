"""
In-app messages between a student and their therapists: one conversation per
student. Students can only read and write their own conversation; therapists
can open any student's. Each side has its own "read up to" time, so both see
an unread count.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

MESSAGES_FILE = Path(__file__).resolve().parents[2] / "data" / "messages.json"
MAX_LENGTH = 2000
_lock = threading.Lock()


def _empty() -> dict:
    return {"messages": [], "read": {"student": None, "therapist": None}}


def _load() -> dict[str, dict]:
    if not MESSAGES_FILE.exists():
        return {}
    try:
        return json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MESSAGES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(MESSAGES_FILE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _view(thread: dict, viewer_role: str) -> dict:
    """The conversation as one side sees it: messages from the other side
    after this side's read time are unread."""
    read_at = thread["read"].get(viewer_role)
    messages = [
        {**m, "unread": m["from_role"] != viewer_role and (read_at is None or m["at"] > read_at)}
        for m in thread["messages"]
    ]
    return {"messages": messages, "unread": sum(1 for m in messages if m["unread"])}


def thread(student: str, viewer_role: str) -> dict:
    with _lock:
        return _view(_load().get(normalize_user_id(student), _empty()), viewer_role)


def send(student: str, sender: str, sender_role: str, text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("The message is empty.")
    key = normalize_user_id(student)
    message = {
        "id": uuid.uuid4().hex,
        "from": normalize_user_id(sender),
        "from_role": sender_role,
        "text": text[:MAX_LENGTH],
        "at": _now(),
    }
    with _lock:
        data = _load()
        t = data.setdefault(key, _empty())
        t["messages"].append(message)
        t["read"][sender_role] = message["at"]  # your own message counts as read
        _save(data)
        return _view(t, sender_role)


def mark_read(student: str, viewer_role: str) -> dict:
    key = normalize_user_id(student)
    with _lock:
        data = _load()
        t = data.setdefault(key, _empty())
        t["read"][viewer_role] = _now()
        _save(data)
        return _view(t, viewer_role)


def unread_for_therapists() -> dict[str, int]:
    """Unread student messages per student, for the therapist portal."""
    with _lock:
        data = _load()
    return {student: _view(t, "therapist")["unread"] for student, t in data.items() if _view(t, "therapist")["unread"]}


def delete_student(student: str) -> None:
    key = normalize_user_id(student)
    with _lock:
        data = _load()
        if data.pop(key, None) is not None:
            _save(data)
