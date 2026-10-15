"""
Registered users (students and therapists).

Stores each account's name, role, registration time and a salted password
hash (see auth.py). Accounts created before passwords existed have no hash;
their first login sets one.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

USERS_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"
# Accounts created by scripts/seed_demo.py. Anything they produce is synthetic.
DEMO_SUFFIX = "@demo.local"

_lock = threading.Lock()


def is_demo_account(email: str) -> bool:
    return normalize_user_id(email).endswith(DEMO_SUFFIX)


def _load() -> dict[str, dict]:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(USERS_FILE)


def public(user: dict) -> dict:
    """User fields that are safe to return to the browser."""
    return {k: v for k, v in user.items() if k != "password_hash"}


def create_user(email: str, name: str, role: str, password_hash: str) -> dict:
    user_id = normalize_user_id(email)
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "email": user_id,
        "name": name.strip() or user_id.split("@")[0],
        "role": role,
        "registered_at": now,
        "last_login": now,
        "password_hash": password_hash,
    }
    with _lock:
        data = _load()
        data[user_id] = user
        _save(data)
    return user


def update_user(email: str, fields: dict) -> dict | None:
    user_id = normalize_user_id(email)
    with _lock:
        data = _load()
        if user_id not in data:
            return None
        data[user_id].update(fields)
        _save(data)
        return data[user_id]


def get_user(email: str) -> dict | None:
    with _lock:
        return _load().get(normalize_user_id(email))


def list_users() -> list[dict]:
    with _lock:
        return list(_load().values())
