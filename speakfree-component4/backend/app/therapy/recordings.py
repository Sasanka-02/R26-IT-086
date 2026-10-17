"""
Practice recordings shared with the therapist.

After a student saves an attempt, the browser uploads that attempt's audio
recording so the therapist can listen to it and give a clinical rating.
Students can switch sharing off on their Privacy tab (`share_recordings` on
the account); deleting the account deletes every recording.

Files live under data/recordings/<hashed student id>/<record id>.<ext> — the
folder name is a hash, so file listings don't expose email addresses — and
are only ever served through the API, with the same access rules as the
student's results (the student themself or a therapist).
"""

import hashlib
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.therapy.progress_store import normalize_user_id

RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "data" / "recordings"
MAX_BYTES = 20 * 1024 * 1024  # about 20 minutes of compressed speech
TYPES = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}
_lock = threading.Lock()


def _folder(student: str) -> Path:
    digest = hashlib.sha256(normalize_user_id(student).encode()).hexdigest()[:24]
    return RECORDINGS_DIR / digest


def base_type(content_type: str | None) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def save(student: str, record_id: str, data: bytes, content_type: str) -> dict:
    kind = base_type(content_type)
    if kind not in TYPES:
        raise ValueError(f"Unsupported audio type: {kind or 'none'}")
    if not data:
        raise ValueError("The recording is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("The recording is too large.")
    folder = _folder(student)
    with _lock:
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob(f"{record_id}.*"):  # replace an earlier upload
            old.unlink()
        (folder / f"{record_id}.{TYPES[kind]}").write_bytes(data)
    return {"content_type": kind, "bytes": len(data), "uploaded_at": datetime.now(timezone.utc).isoformat()}


def load(student: str, record_id: str) -> tuple[bytes, str] | None:
    folder = _folder(student)
    with _lock:
        files = list(folder.glob(f"{record_id}.*")) if folder.exists() else []
        if not files:
            return None
        ext = files[0].suffix.lstrip(".")
        kind = next((t for t, e in TYPES.items() if e == ext), "application/octet-stream")
        return files[0].read_bytes(), kind


def delete_student(student: str) -> None:
    with _lock:
        shutil.rmtree(_folder(student), ignore_errors=True)
