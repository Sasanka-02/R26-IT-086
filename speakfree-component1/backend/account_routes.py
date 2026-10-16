"""
Account settings and appointment requests (platform features shared by every component).

  PATCH /api/v1/auth/me                         update display name
  POST  /api/v1/auth/change-password            current + new password (bcrypt), min 8 chars
  GET   /api/v1/appointments                    the account's own requests
  POST  /api/v1/appointments                    request a session with a speech-language pathologist
  POST  /api/v1/appointments/{id}/cancel        cancel a pending / confirmed request
  GET   /api/v1/admin/appointments              admin: every request (filter by status)
  PATCH /api/v1/admin/appointments/{id}         admin: confirm (with date-time) / decline, with a note
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_user, get_owned_patient, hash_password, require_admin, verify_password
from database import AppointmentRequest, User, as_utc, get_db

router = APIRouter()


# ============================================================================= account
class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=64)


@router.patch("/api/v1/auth/me", tags=["auth"])
def update_me(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="The administrator account is managed in config.py")
    user.full_name = body.full_name.strip()
    # a self-registered patient's patient record carries the same name
    for p in user.patients:
        if p.is_self:
            p.full_name = user.full_name
    db.commit()
    return {"full_name": user.full_name}


@router.post("/api/v1/auth/change-password", status_code=204, tags=["auth"])
def change_password(body: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="The administrator password is managed in config.py")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=422, detail="Choose a password different from the current one")
    user.password_hash = hash_password(body.new_password)
    db.commit()


# ============================================================================= appointments
class AppointmentCreate(BaseModel):
    patient_id: str
    preferred_date: date
    preferred_time: Literal["morning", "afternoon", "evening"]
    mode: Literal["online", "in_person"]
    reason: str = Field(min_length=5, max_length=1000)


class AppointmentDecision(BaseModel):
    status: Literal["confirmed", "declined"]
    scheduled_at: datetime | None = None
    admin_note: str | None = Field(default=None, max_length=1000)


def _out(a: AppointmentRequest, admin: bool = False) -> dict:
    data = {
        "id": a.id, "patient_id": a.patient_id, "patient_name": a.patient.full_name,
        "preferred_date": a.preferred_date.isoformat(), "preferred_time": a.preferred_time, "mode": a.mode,
        "reason": a.reason, "status": a.status, "admin_note": a.admin_note,
        "scheduled_at": as_utc(a.scheduled_at).isoformat() if a.scheduled_at else None,
        "created_at": as_utc(a.created_at).isoformat(),
    }
    if admin:
        data |= {"requested_by": a.user.full_name, "requested_by_email": a.user.email, "requested_by_role": a.user.role}
    return data


@router.get("/api/v1/appointments", tags=["appointments"])
def my_appointments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AppointmentRequest).where(AppointmentRequest.user_id == user.id)
                      .order_by(AppointmentRequest.created_at.desc())).all()
    return [_out(a) for a in rows]


@router.post("/api/v1/appointments", status_code=201, tags=["appointments"])
def request_appointment(body: AppointmentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, body.patient_id)
    if body.preferred_date < date.today():
        raise HTTPException(status_code=422, detail="Choose a date from today onwards")
    a = AppointmentRequest(user_id=user.id, patient_id=patient.id, preferred_date=body.preferred_date,
                           preferred_time=body.preferred_time, mode=body.mode, reason=body.reason.strip())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.post("/api/v1/appointments/{appointment_id}/cancel", tags=["appointments"])
def cancel_appointment(appointment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(AppointmentRequest, appointment_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if a.status in ("declined", "cancelled"):
        raise HTTPException(status_code=409, detail=f"This request is already {a.status}")
    a.status = "cancelled"
    db.commit()
    return _out(a)


@router.get("/api/v1/admin/appointments", tags=["admin"])
def admin_appointments(status: str | None = Query(None), _: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(AppointmentRequest).order_by(AppointmentRequest.created_at.desc())
    if status:
        q = q.where(AppointmentRequest.status == status)
    return [_out(a, admin=True) for a in db.scalars(q).all()]


@router.patch("/api/v1/admin/appointments/{appointment_id}", tags=["admin"])
def admin_decide(appointment_id: int, body: AppointmentDecision, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    a = db.get(AppointmentRequest, appointment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if a.status == "cancelled":
        raise HTTPException(status_code=409, detail="The patient cancelled this request")
    if body.status == "confirmed" and body.scheduled_at is None:
        raise HTTPException(status_code=422, detail="Give the confirmed date and time")
    a.status = body.status
    a.scheduled_at = body.scheduled_at if body.status == "confirmed" else None
    a.admin_note = (body.admin_note or "").strip() or None
    db.commit()
    return _out(a, admin=True)
