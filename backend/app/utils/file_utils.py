import os
import uuid
from pathlib import Path

from fastapi import UploadFile


def safe_extension(filename: str | None, content_type: str | None) -> str:
    """Derive a safe file extension, defaulting by content type if the
    filename is missing or suspicious."""
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in {".webm", ".wav", ".mp4", ".ogg", ".m4a"}:
            return ext

    mapping = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp4": ".mp4",
        "audio/ogg": ".ogg",
    }
    return mapping.get(content_type or "", ".bin")


async def save_upload(upload_file: UploadFile, upload_dir: str) -> str:
    """Streams the upload to disk under a random filename and returns the path."""
    os.makedirs(upload_dir, exist_ok=True)
    ext = safe_extension(upload_file.filename, upload_file.content_type)
    dest_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{ext}")

    with open(dest_path, "wb") as f:
        while chunk := await upload_file.read(1024 * 1024):
            f.write(chunk)

    return dest_path


def cleanup_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
