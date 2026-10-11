"""
Per-user practice history.

Stores one small summary record per completed exercise (score, duration,
pause counts, self-rating) — never audio — in a local JSON file, so each
user's dashboard, plan and assistant reflect their own practice and
survive a backend restart.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "user_progress.json"

_lock = threading.Lock()


def normalize_user_id(user_id: str) -> str:
    return user_id.strip().lower()


def _load() -> dict[str, list[dict]]:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, list[dict]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def get_records(user_id: str) -> list[dict]:
    """All records for a user, oldest first."""
    with _lock:
        return list(_load().get(normalize_user_id(user_id), []))


def add_record(user_id: str, record: dict) -> dict:
    stored = {
        "id": uuid.uuid4().hex,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    with _lock:
        data = _load()
        data.setdefault(normalize_user_id(user_id), []).append(stored)
        _save(data)
    return stored


def update_record(user_id: str, record_id: str, fields: dict) -> dict | None:
    with _lock:
        data = _load()
        for record in data.get(normalize_user_id(user_id), []):
            if record["id"] == record_id:
                record.update(fields)
                _save(data)
                return record
    return None


def all_records() -> dict[str, list[dict]]:
    """Every user's records, keyed by user id (oldest first)."""
    with _lock:
        return _load()
