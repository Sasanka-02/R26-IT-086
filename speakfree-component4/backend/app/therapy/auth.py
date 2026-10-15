"""
Authentication and authorisation.

* Passwords are stored as PBKDF2-HMAC-SHA256 hashes (200 000 iterations,
  16-byte random salt) — never in plain text.
* Login returns a signed token: base64url(payload) + "." + HMAC-SHA256
  signature. The payload holds the user id, role and expiry; tampering
  with any of them breaks the signature.
* Every personal endpoint checks the token: students may only read or
  write their own data; therapist endpoints require the therapist role.
* Registering as a therapist requires the clinic invite code
  (THERAPIST_INVITE_CODE), so a student cannot simply sign up as one.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, Header, HTTPException, status

from app.therapy.progress_store import normalize_user_id

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = 7 * 24 * 3600
SECRET_FILE = Path(__file__).resolve().parents[2] / "data" / "auth_secret.key"
THERAPIST_INVITE_CODE = os.environ.get("THERAPIST_INVITE_CODE", "SPEAKFREE-CLINIC")


def _secret() -> bytes:
    env = os.environ.get("AUTH_SECRET")
    if env:
        return env.encode()
    if not SECRET_FILE.exists():
        SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        SECRET_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
    return SECRET_FILE.read_text(encoding="utf-8").strip().encode()


# --- Passwords ---------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- Tokens ------------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(user: dict) -> str:
    payload = {"sub": user["email"], "role": user["role"], "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_token(token: str) -> dict | None:
    try:
        body, signature = token.split(".")
    except ValueError:
        return None
    expected = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


# --- Login rate limit -----------------------------------------------------------
# After MAX_FAILED_LOGINS wrong passwords for one account within the window,
# further attempts are refused until the oldest failure expires. This slows
# password guessing without locking the real user out for long.

MAX_FAILED_LOGINS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = {}


def _recent_failures(email: str) -> list[float]:
    cutoff = time.time() - LOGIN_WINDOW_SECONDS
    recent = [t for t in _failed_logins.get(normalize_user_id(email), []) if t > cutoff]
    _failed_logins[normalize_user_id(email)] = recent
    return recent


def login_blocked_for(email: str) -> int:
    """Seconds until another login attempt is allowed (0 = allowed now)."""
    recent = _recent_failures(email)
    if len(recent) < MAX_FAILED_LOGINS:
        return 0
    return int(recent[0] + LOGIN_WINDOW_SECONDS - time.time()) + 1


def record_failed_login(email: str) -> None:
    _recent_failures(email).append(time.time())


def clear_failed_logins(email: str) -> None:
    _failed_logins.pop(normalize_user_id(email), None)


# --- FastAPI dependencies ----------------------------------------------------

def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    payload = decode_token(authorization.removeprefix("Bearer ").strip())
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again.")
    return {"email": payload["sub"], "role": payload["role"]}


def require_therapist(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "therapist":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Therapist access only.")
    return user


def ensure_can_access(user: dict, student_id: str) -> None:
    """Students may only access their own data; therapists may access any student."""
    if user["role"] == "therapist":
        return
    if normalize_user_id(student_id) != user["email"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only access your own data.")
