"""
Authentication helpers: bcrypt password hashing, JWT bearer tokens and login verification.

Login verification (brute-force protection):
  • unknown email or wrong password  -> the SAME generic 401 (no account enumeration)
  • MAX_FAILED_LOGINS wrong passwords -> account locked for LOCKOUT_MINUTES, 423 "Account locked…"
  • successful login                  -> failed_logins reset, last_login_at recorded
"""
import math
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import Patient, User, as_utc, get_db, utcnow

_bearer = HTTPBearer(auto_error=False)

INVALID_CREDENTIALS = "Incorrect email or password"


def _pw_bytes(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; truncate explicitly so long passwords never error.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Used to spend the same bcrypt time when the email does not exist (timing-safe 401).
_DUMMY_HASH = hash_password("speakfree-timing-equaliser")


def _locked_response(locked_until: datetime) -> HTTPException:
    minutes = max(1, math.ceil((locked_until - utcnow()).total_seconds() / 60))
    return HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail=f"Account locked, try again in {minutes} minute{'s' if minutes != 1 else ''}",
    )


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials and update the lockout counters. Raises 401 / 423 on failure."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    now = utcnow()
    locked_until = as_utc(user.locked_until)
    if locked_until and locked_until > now:
        raise _locked_response(locked_until)

    if not verify_password(password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_logins = 0  # a fresh count starts once the lock expires
            db.commit()
            raise _locked_response(user.locked_until)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    return user


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user.id), "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_clinician(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("clinician", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only clinicians can manage the task library")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Admin-only routes (patient directory, any patient's history and technical results)."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def can_view_patient(user: User, patient: Patient) -> bool:
    """Owners see their own patients; the admin can read every patient's results."""
    return user.role == "admin" or patient.owner_user_id == user.id


def get_owned_patient(db: Session, user: User, patient_id: str) -> Patient:
    """Return the patient only if the current account is allowed to access it."""
    patient = db.get(Patient, patient_id)
    if patient is None or patient.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
