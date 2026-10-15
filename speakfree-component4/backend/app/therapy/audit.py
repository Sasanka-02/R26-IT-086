"""
Audit log: an append-only record of who changed what. Every therapist action
on a student (assignments, level, goals, notes, ratings, plan reviews),
screening results and account deletions are written here, one JSON object
per line, so changes can be traced afterwards.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

AUDIT_FILE = Path(__file__).resolve().parents[2] / "data" / "audit_log.jsonl"
_lock = threading.Lock()


def log(actor: str, action: str, subject: str | None = None, **details) -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "subject": subject,
        **({"details": details} if details else {}),
    }
    with _lock:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def recent(limit: int = 100, subject: str | None = None) -> list[dict]:
    with _lock:
        if not AUDIT_FILE.exists():
            return []
        lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    if subject:
        entries = [e for e in entries if e.get("subject") == subject or e.get("actor") == subject]
    return list(reversed(entries))[:limit]
