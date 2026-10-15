"""
SpeakFree – Component 1: Noise-Robust Speech Screening & Feature Extraction
FastAPI application (REST + WebSocket)

Run:   uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3
Docs:  http://localhost:8000/docs

Tasks are delivered from the assessment_tasks table (seed it with `python seed.py`);
task_bank.py is seed data only.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from age_brackets import MAX_AGE, MIN_AGE, age_from_dob, bracket_for_age, bracket_info
from audio_preprocessing import AudioDecodeError, decode_audio, preprocess, waveform_peaks
from auth import (
    authenticate,
    can_view_patient,
    create_access_token,
    decode_token,
    get_current_user,
    get_owned_patient,
    hash_password,
    require_admin,
    require_clinician,
    verify_password,
)
from config import settings
from database import (
    TASK_TYPES,
    as_utc,
    Analysis,
    AssessmentTask,
    Patient,
    ScreeningSession,
    SessionLocal,
    TaskAttempt,
    User,
    get_db,
    run_migrations,
    utcnow,
)
from schemas import (
    AdminPatientProfile,
    AdminPatientRow,
    AdminRecording,
    AdminSessionRow,
    AdminTaskOut,
    AnalysisSummary,
    AnalyzeResponse,
    FinalizeSessionRequest,
    LoginRequest,
    PatientCreate,
    PatientOut,
    RegisterRequest,
    SessionListItem,
    SessionSummary,
    TokenResponse,
    UserOut,
)
from streaming import chunk_metrics, hub
from session_summary import summarise_session
from task_service import TaskLibraryEmpty, image_url, pick_tasks, task_set_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("speakfree.c1")

ALLOWED_EXTENSIONS = {".webm", ".wav", ".ogg", ".m4a", ".mp3", ".mp4"}

TASK_IMAGE_DIR = os.path.join(settings.static_dir, "tasks")
os.makedirs(TASK_IMAGE_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_migrate:
        run_migrations()
    with SessionLocal() as db:
        task_count = db.scalar(select(func.count()).select_from(AssessmentTask)) or 0
        ensure_admin(db)
    if task_count == 0:
        log.warning("The task library is empty – run `python seed.py` in the backend folder.")
    log.info("Database ready (%d tasks). Whisper model '%s' loads on first analysis.", task_count, settings.whisper_model)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.schema_version,
    description="ASR confidence biomarker (Whisper log-probabilities) + acoustic feature extraction.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Task images (backend/static/tasks/<task_id>.<ext>) – never audio.
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


# ============================================================================= helpers
def patient_out(p: Patient) -> PatientOut:
    age = age_from_dob(p.date_of_birth)
    b = bracket_for_age(age)
    return PatientOut(
        id=p.id,
        full_name=p.full_name,
        date_of_birth=p.date_of_birth,
        age=age,
        age_bracket=bracket_info(b) if b else None,
        is_self=p.is_self,
    )


def user_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name, role=u.role,
        patients=[patient_out(p) for p in u.patients],
    )


def require_supported_age(dob, who: str = "Patient") -> int:
    age = age_from_dob(dob)
    if not (MIN_AGE <= age <= MAX_AGE):
        raise HTTPException(
            status_code=422,
            detail=f"{who} must be between {MIN_AGE} and {MAX_AGE} years old (calculated age: {age}).",
        )
    return age


def ensure_admin(db: Session) -> User:
    """Create the built-in admin account (or re-sync its password/role) from config.py."""
    email = settings.admin_email.lower()
    admin = db.scalar(select(User).where(User.email == email))
    if admin is None:
        admin = User(email=email, full_name=settings.admin_name, password_hash=hash_password(settings.admin_password),
                     role="admin", consent_given_at=utcnow())
        db.add(admin)
        log.info("Created admin account %s", email)
    else:
        if admin.role != "admin":
            admin.role = "admin"
        if not verify_password(settings.admin_password, admin.password_hash):
            admin.password_hash = hash_password(settings.admin_password)
    db.commit()
    return admin


def get_asr():
    from asr_service import WhisperConfidenceASR  # lazy: heavy torch import

    return WhisperConfidenceASR.get(
        settings.whisper_model, settings.whisper_device, settings.verbatim_prompt, settings.dysfluency_threshold,
        settings.no_speech_threshold, settings.max_words_per_sec,
    )


# ============================================================================= system
@app.get("/api/v1/health", tags=["system"])
def health():
    from asr_service import WhisperConfidenceASR

    return {
        "status": "ok",
        "component": "C1-speech-screening",
        "schema_version": settings.schema_version,
        "whisper_model": settings.whisper_model,
        "whisper_loaded": WhisperConfidenceASR.is_loaded(),
        "noise_reduction": settings.enable_noise_reduction,
        "hubert": settings.enable_hubert,
    }


@app.post("/api/v1/system/warmup", tags=["system"])
async def warmup():
    """Pre-load Whisper so the first real analysis is fast."""
    await run_in_threadpool(get_asr)
    return {"whisper_loaded": True, "model": settings.whisper_model}


# ============================================================================= auth
@app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201, tags=["auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # server-side validation (password length / email format / consent are enforced by RegisterRequest)
    if body.role == "patient":
        if body.date_of_birth is None:
            raise HTTPException(status_code=422, detail="Date of birth is required for patients")
        require_supported_age(body.date_of_birth)
    elif body.role == "guardian":
        if not body.child_full_name or len(body.child_full_name.strip()) < 2 or body.child_date_of_birth is None:
            raise HTTPException(status_code=422, detail="Child's name and date of birth are required")
        require_supported_age(body.child_date_of_birth, "Child")

    user = User(
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        consent_given_at=utcnow(),
    )
    db.add(user)
    db.flush()

    if body.role == "patient":
        db.add(Patient(owner_user_id=user.id, full_name=user.full_name, date_of_birth=body.date_of_birth, is_self=True))
    elif body.role == "guardian":
        db.add(Patient(owner_user_id=user.id, full_name=body.child_full_name.strip(), date_of_birth=body.child_date_of_birth))

    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=user_out(user))


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """401 (same message) for unknown email or wrong password; 423 while the account is locked."""
    user = authenticate(db, body.email, body.password)
    return TokenResponse(access_token=create_access_token(user), user=user_out(user))


@app.get("/api/v1/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user_out(user)


# ============================================================================= patients
@app.get("/api/v1/patients", response_model=list[PatientOut], tags=["patients"])
def list_patients(user: User = Depends(get_current_user)):
    return [patient_out(p) for p in user.patients]


@app.post("/api/v1/patients", response_model=PatientOut, status_code=201, tags=["patients"])
def create_patient(body: PatientCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in ("patient", "admin"):
        raise HTTPException(status_code=403, detail=f"{user.role.title()} accounts cannot add patients")
    require_supported_age(body.date_of_birth)
    p = Patient(owner_user_id=user.id, full_name=body.full_name.strip(), date_of_birth=body.date_of_birth)
    db.add(p)
    db.commit()
    db.refresh(p)
    return patient_out(p)


# ============================================================================= dynamic task engine
@app.get("/api/v1/tasks", tags=["tasks"])
def tasks_for_patient(
    request: Request,
    patient_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Age (from DOB, today) -> bracket -> one active task per type (three questions), preferring
    tasks this patient has attempted least. See task_service.py.
    """
    patient = get_owned_patient(db, user, patient_id)
    age = age_from_dob(patient.date_of_birth)
    bracket = bracket_for_age(age)
    if bracket is None:
        raise HTTPException(status_code=422, detail=f"Age {age} is outside the supported 6–20 range")
    try:
        picked = pick_tasks(db, patient.id, bracket)
    except TaskLibraryEmpty as exc:
        raise HTTPException(
            status_code=503, detail=f"No active '{exc}' task for bracket {bracket}. Task library is empty – run python seed.py"
        ) from exc
    return {
        "patient_id": patient.id,
        "age": age,
        "age_bracket": bracket_info(bracket),
        "tasks": task_set_payload(picked, str(request.base_url)),
    }


# ============================================================================= analysis pipeline
def run_pipeline(path: str, task_type: str, reference_text: str | None, keywords: list[str] | None, age_bracket: int) -> dict:
    """CPU/GPU-heavy work. Runs in a worker thread so the event loop stays responsive."""
    from feature_extraction import extract_features
    from scoring import compute_scores

    t0 = time.perf_counter()

    # 1) ingestion + pre-processing (noise reduction, VAD, edge trimming, pause detection)
    raw = decode_audio(path)
    pre = preprocess(
        raw,
        enable_noise_reduction=settings.enable_noise_reduction,
        significant_pause_sec=settings.significant_pause_sec,
    )
    if not pre.speech_intervals or pre.clean_audio.size < 0.3 * pre.sample_rate:
        raise HTTPException(status_code=422, detail="No speech detected. Please record again in a quieter place, closer to the microphone.")

    # 2) Whisper transcription + log-probability confidence (Eq. 1–3)
    asr = get_asr()
    tr = asr.transcribe(pre.clean_audio, time_offset=pre.trim_offset_sec, sample_rate=pre.sample_rate)
    words = [w.to_dict() for w in tr.words]
    if not words:
        if tr.rejected_segments:
            log.info("All %d segments rejected by hallucination guard: %s", len(tr.rejected_segments), tr.rejected_segments)
            if all(r["reason"].startswith("repetition loop") for r in tr.rejected_segments):
                detail = ("The speech model could not get a reliable transcript of this recording (it kept repeating "
                          "the same word). Please record again and answer in one or two full sentences.")
            else:
                detail = ("No clear speech was found – the recording sounds like noise, a tone or silence. "
                          "Please record again, speaking clearly about 20–30 cm from the microphone.")
            raise HTTPException(status_code=422, detail=detail)
        raise HTTPException(status_code=422, detail="Speech was detected but no words could be recognised. Please try again.")

    # 3) acoustic + prosodic features
    features = extract_features(pre, words, settings.enable_hubert, settings.hubert_model)

    # 4) explainable scores
    reference = reference_text if task_type == "reading" else None
    scores = compute_scores(
        words=words,
        transcript=tr.transcript,
        overall_confidence=tr.overall_confidence_percent,
        features=features,
        age_bracket=age_bracket,
        task_type=task_type,
        reference_text=reference,
        keywords=keywords,
        threshold=settings.dysfluency_threshold,
    )

    return {
        "transcript": tr.transcript,
        "reference_text": reference,
        "overall_confidence_percent": round(tr.overall_confidence_percent, 2),
        "dysfluency_threshold": settings.dysfluency_threshold,
        **scores,
        "word_segments": words,
        "pauses": [p.to_dict() for p in pre.pauses],
        "acoustic_features": features,
        "segments": tr.segments,
        "preprocessing": {
            "sample_rate": pre.sample_rate,
            "trim_offset_sec": pre.trim_offset_sec,
            "original_duration_sec": pre.original_duration_sec,
            "noise_reduction_applied": pre.noise_reduction_applied,
            "vad_speech_intervals": [[s, e] for s, e in pre.speech_intervals],
            "significant_pause_threshold_sec": settings.significant_pause_sec,
            "raw_audio_retained": False,
        },
        "waveform_peaks": waveform_peaks(pre.raw_audio),
        "model": {
            "asr": f"openai-whisper/{tr.model_name}",
            "device": tr.device,
            "token_count": len(tr.all_token_logprobs),
            "verbatim_prompt": bool(settings.verbatim_prompt),
            "rejected_segments": tr.rejected_segments,
        },
        "processing_time_ms": int((time.perf_counter() - t0) * 1000),
    }


@app.post("/api/v1/analyze", response_model=AnalyzeResponse, tags=["analysis"])
async def analyze(
    audio: UploadFile = File(..., description="Single audio blob (.webm or .wav)"),
    session_id: str = Form(...),
    patient_id: str = Form(...),
    age_bracket: int = Form(..., ge=1, le=7),
    task_type: str = Form("reading"),
    task_id: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if task_type not in TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"task_type must be one of {TASK_TYPES}")

    patient = get_owned_patient(db, user, patient_id)
    actual_bracket = bracket_for_age(age_from_dob(patient.date_of_birth))
    if actual_bracket != age_bracket:
        log.warning("age_bracket %s sent but patient is in bracket %s – using patient's bracket", age_bracket, actual_bracket)
        age_bracket = actual_bracket or age_bracket

    task = db.get(AssessmentTask, task_id)
    if task is None:
        raise HTTPException(status_code=422, detail=f"Unknown task_id '{task_id}'")
    if task.task_type != task_type:
        raise HTTPException(status_code=422, detail=f"Task '{task_id}' is a {task.task_type} task, not {task_type}")
    if task.age_bracket != age_bracket:
        log.warning("Task %s is for bracket %s but patient is in bracket %s", task.id, task.age_bracket, age_bracket)
    reference_text = task.content_text if task.task_type == "reading" else None
    keywords = list(task.keywords or []) if task.task_type == "picture" else None

    ext = os.path.splitext(audio.filename or "")[1].lower() or ".webm"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type '{ext}'. Use .webm or .wav")

    data = await audio.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Audio larger than {settings.max_upload_mb} MB")
    if len(data) < 1000:
        raise HTTPException(status_code=422, detail="Audio file is empty or too short")

    # Privacy: audio is written to a temp file only for decoding and deleted immediately after.
    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        try:
            result = await run_in_threadpool(run_pipeline, tmp_path, task_type, reference_text, keywords, age_bracket)
        except AudioDecodeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    analysis_id = str(uuid.uuid4())
    payload = {
        "schema_version": settings.schema_version,
        "component": "C1-speech-screening",
        "analysis_id": analysis_id,
        "session_id": session_id,
        "patient_id": patient.id,
        "task_type": task_type,
        "task_id": task.id,
        "age_bracket": age_bracket,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }

    db.add(Analysis(
        id=analysis_id,
        session_id=session_id,
        patient_id=patient.id,
        task_type=task_type,
        task_id=task.id,
        age_bracket=age_bracket,
        overall_speech_score=result["overall_speech_score"],
        overall_confidence_percent=result["overall_confidence_percent"],
        result_json=json.dumps(payload),
    ))
    db.flush()  # analyses row must exist before the attempt references it (FK)
    db.add(TaskAttempt(patient_id=patient.id, task_id=task.id, analysis_id=analysis_id))
    db.commit()
    return payload


def _owned_analysis(db: Session, user: User, analysis_id: str) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None or not can_view_patient(user, a.patient):
        raise HTTPException(status_code=404, detail="Result not found")
    return a


@app.get("/api/v1/results/{analysis_id}", response_model=AnalyzeResponse, tags=["analysis"])
def get_result(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return json.loads(_owned_analysis(db, user, analysis_id).result_json)


@app.get("/api/v1/sessions/{session_id}/results", response_model=list[AnalyzeResponse], tags=["analysis"])
def session_results(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """All task results of one screening session – used by Components 2 and 3."""
    rows = db.scalars(select(Analysis).where(Analysis.session_id == session_id).order_by(Analysis.created_at)).all()
    return [json.loads(r.result_json) for r in rows if can_view_patient(user, r.patient)]


def _task_titles(db: Session, task_ids: list[str]) -> dict[str, str]:
    """task_id → human title (the question itself for pre-defined questions)."""
    rows = db.scalars(select(AssessmentTask).where(AssessmentTask.id.in_(task_ids))).all()
    return {t.id: (t.content_text if t.task_type == "questions" else t.title) for t in rows}


@app.post("/api/v1/sessions/{session_id}/finalize", response_model=SessionSummary, tags=["analysis"])
def finalize_session(session_id: str, body: FinalizeSessionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Called after every recording of a screening session has been analysed ("Analyse Now").
    Pools all recordings into the session-level Component 1 output and stores it.
    Calling it again recomputes the summary (e.g. after a retried recording).
    """
    patient = get_owned_patient(db, user, body.patient_id)
    rows = db.scalars(
        select(Analysis).where(Analysis.session_id == session_id, Analysis.patient_id == patient.id).order_by(Analysis.created_at)
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No analysed recordings found for this session")

    # if a task was recorded twice in the session, keep only the latest attempt
    latest: dict[tuple[str, str], Analysis] = {}
    for r in rows:
        latest[(r.task_type, r.task_id)] = r
    results = [json.loads(r.result_json) for r in latest.values()]

    summary = summarise_session(
        results,
        session_id=session_id,
        patient_id=patient.id,
        threshold=settings.dysfluency_threshold,
        task_titles=_task_titles(db, [r["task_id"] for r in results]),
        schema_version=settings.schema_version,
    )

    row = db.get(ScreeningSession, session_id)
    if row is None:
        row = ScreeningSession(id=session_id, patient_id=patient.id)
        db.add(row)
    elif row.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Session belongs to a different patient")
    row.age_bracket = summary["age_bracket"]
    row.recording_count = summary["recording_count"]
    row.overall_speech_score = summary["overall_speech_score"]
    row.overall_confidence_percent = summary["overall_confidence_percent"]
    row.summary_json = json.dumps(summary)
    row.created_at = utcnow()
    db.commit()
    return summary


def _owned_session(db: Session, user: User, session_id: str) -> ScreeningSession:
    s = db.get(ScreeningSession, session_id)
    if s is None or not can_view_patient(user, s.patient):
        raise HTTPException(status_code=404, detail="Session summary not found. Run the analysis first.")
    return s


@app.get("/api/v1/sessions/{session_id}/summary", response_model=SessionSummary, tags=["analysis"])
def session_summary(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Session-level Component 1 output – the hand-off to Components 2 and 3."""
    return json.loads(_owned_session(db, user, session_id).summary_json)


@app.get("/api/v1/patients/{patient_id}/sessions", response_model=list[SessionListItem], tags=["analysis"])
def patient_sessions(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    rows = db.scalars(
        select(ScreeningSession).where(ScreeningSession.patient_id == patient.id).order_by(ScreeningSession.created_at)
    ).all()
    out = []
    for r in rows:
        indicator = json.loads(r.summary_json)["screening_indicator"]
        out.append(SessionListItem(
            session_id=r.id, patient_id=r.patient_id, created_at=r.created_at, recording_count=r.recording_count,
            overall_speech_score=r.overall_speech_score, overall_confidence_percent=r.overall_confidence_percent,
            severity_hint=indicator["severity_hint"], label=indicator["label"],
        ))
    return out


@app.get("/api/v1/patients/{patient_id}/history", response_model=list[AnalysisSummary], tags=["analysis"])
def patient_history(patient_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_owned_patient(db, user, patient_id)
    rows = db.scalars(select(Analysis).where(Analysis.patient_id == patient.id).order_by(Analysis.created_at)).all()
    return [
        AnalysisSummary(
            analysis_id=r.id, session_id=r.session_id, task_type=r.task_type, task_id=r.task_id,
            created_at=r.created_at, overall_speech_score=r.overall_speech_score,
            overall_confidence_percent=r.overall_confidence_percent,
        )
        for r in rows
    ]


# ============================================================================= clinician task library
IMAGE_TYPES = {  # extension -> (accepted content types, magic-byte check)
    ".png": ({"image/png"}, lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ({"image/jpeg"}, lambda b: b.startswith(b"\xff\xd8\xff")),
    ".jpeg": ({"image/jpeg"}, lambda b: b.startswith(b"\xff\xd8\xff")),
    ".webp": ({"image/webp"}, lambda b: len(b) > 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}
TYPE_PREFIX = {"reading": "read", "picture": "pic", "scenario": "scn", "questions": "q"}


async def _read_task_image(image: UploadFile) -> tuple[bytes, str]:
    """Validate an uploaded task image (jpg/png/webp, ≤ MAX_IMAGE_MB, real image bytes)."""
    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        raise HTTPException(status_code=422, detail="Image must be a .jpg, .png or .webp file")
    content_types, looks_valid = IMAGE_TYPES[ext]
    if image.content_type and image.content_type not in content_types:
        raise HTTPException(status_code=422, detail=f"Image content type '{image.content_type}' does not match {ext}")
    limit = settings.max_image_mb * 1024 * 1024
    data = await image.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"Image larger than {settings.max_image_mb} MB")
    if not looks_valid(data):
        raise HTTPException(status_code=422, detail=f"File is not a valid {ext.lstrip('.').upper()} image")
    return data, (".jpg" if ext == ".jpeg" else ext)


def _save_task_image(task: AssessmentTask, data: bytes, ext: str) -> None:
    _delete_task_image(task)
    with open(os.path.join(TASK_IMAGE_DIR, task.id + ext), "wb") as fh:
        fh.write(data)
    task.image_path = f"tasks/{task.id}{ext}"


def _delete_task_image(task: AssessmentTask) -> None:
    if task.image_path:
        path = os.path.join(settings.static_dir, task.image_path)
        if os.path.isfile(path):
            os.remove(path)
    task.image_path = None


def _parse_keywords(raw: str | None) -> list[str]:
    return [k.strip().lower() for k in (raw or "").split(",") if k.strip()]


def _parse_visual(raw: str | None) -> dict | None:
    if raw is None or not raw.strip():
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="visual_json must be valid JSON") from exc
    if not isinstance(value, dict) or value.get("kind") not in ("emoji", "chart"):
        raise HTTPException(status_code=422, detail='visual_json must be an object with "kind": "emoji" or "chart"')
    return value


def _next_task_id(db: Session, bracket: int, task_type: str) -> str:
    prefix = f"b{bracket}-{TYPE_PREFIX[task_type]}-"
    ids = db.scalars(select(AssessmentTask.id).where(AssessmentTask.id.like(prefix + "%"))).all()
    numbers = [int(i[len(prefix):]) for i in ids if i[len(prefix):].isdigit()]
    return f"{prefix}{max(numbers, default=0) + 1}"


def _admin_task_out(task: AssessmentTask, base_url: str, attempts: int) -> AdminTaskOut:
    return AdminTaskOut(
        id=task.id, age_bracket=task.age_bracket, task_type=task.task_type, title=task.title,
        instructions=task.instructions, content_text=task.content_text, image_path=task.image_path,
        image_url=image_url(task, base_url), keywords=list(task.keywords or []), visual_json=task.visual_json,
        max_seconds=task.max_seconds, is_active=task.is_active, created_by_user_id=task.created_by_user_id,
        created_at=task.created_at, attempt_count=attempts,
    )


def _attempts_by_task(db: Session, task_ids: list[str]) -> dict[str, int]:
    if not task_ids:
        return {}
    rows = db.execute(
        select(TaskAttempt.task_id, func.count()).where(TaskAttempt.task_id.in_(task_ids)).group_by(TaskAttempt.task_id)
    ).all()
    return dict(rows)


def _validate_task_fields(age_bracket: int | None, task_type: str | None, max_seconds: int | None) -> None:
    if age_bracket is not None and not 1 <= age_bracket <= 7:
        raise HTTPException(status_code=422, detail="age_bracket must be between 1 and 7")
    if task_type is not None and task_type not in TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"task_type must be one of {', '.join(TASK_TYPES)}")
    if max_seconds is not None and not 10 <= max_seconds <= 300:
        raise HTTPException(status_code=422, detail="max_seconds must be between 10 and 300")


@app.get("/api/v1/admin/tasks", response_model=list[AdminTaskOut], tags=["admin"])
def admin_list_tasks(
    request: Request,
    age_bracket: int | None = Query(None, ge=1, le=7),
    task_type: str | None = Query(None),
    include_inactive: bool = Query(True),
    _: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _validate_task_fields(None, task_type, None)
    q = select(AssessmentTask).order_by(AssessmentTask.age_bracket, AssessmentTask.task_type, AssessmentTask.id)
    if age_bracket is not None:
        q = q.where(AssessmentTask.age_bracket == age_bracket)
    if task_type is not None:
        q = q.where(AssessmentTask.task_type == task_type)
    if not include_inactive:
        q = q.where(AssessmentTask.is_active.is_(True))
    tasks = db.scalars(q).all()
    attempts = _attempts_by_task(db, [t.id for t in tasks])
    return [_admin_task_out(t, str(request.base_url), attempts.get(t.id, 0)) for t in tasks]


@app.post("/api/v1/admin/tasks", response_model=AdminTaskOut, status_code=201, tags=["admin"])
async def admin_create_task(
    request: Request,
    age_bracket: int = Form(...),
    task_type: str = Form(...),
    title: str = Form(..., min_length=2, max_length=200),
    instructions: str = Form(..., min_length=2),
    content_text: str = Form(..., min_length=2),
    max_seconds: int = Form(60),
    keywords: str | None = Form(None),
    visual_json: str | None = Form(None),
    is_active: bool = Form(True),
    image: UploadFile | None = File(None),
    user: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    _validate_task_fields(age_bracket, task_type, max_seconds)
    image_data = await _read_task_image(image) if image is not None and image.filename else None
    task = AssessmentTask(
        id=_next_task_id(db, age_bracket, task_type), age_bracket=age_bracket, task_type=task_type,
        title=title.strip(), instructions=instructions.strip(), content_text=content_text.strip(),
        keywords=_parse_keywords(keywords), visual_json=_parse_visual(visual_json), max_seconds=max_seconds,
        is_active=is_active, created_by_user_id=user.id,
    )
    if image_data:
        _save_task_image(task, *image_data)
    db.add(task)
    db.commit()
    return _admin_task_out(task, str(request.base_url), 0)


@app.patch("/api/v1/admin/tasks/{task_id}", response_model=AdminTaskOut, tags=["admin"])
async def admin_update_task(
    task_id: str,
    request: Request,
    title: str | None = Form(None, min_length=2, max_length=200),
    instructions: str | None = Form(None, min_length=2),
    content_text: str | None = Form(None, min_length=2),
    max_seconds: int | None = Form(None),
    keywords: str | None = Form(None),
    visual_json: str | None = Form(None),
    is_active: bool | None = Form(None),
    remove_image: bool = Form(False),
    image: UploadFile | None = File(None),
    _: User = Depends(require_clinician),
    db: Session = Depends(get_db),
):
    """Edit, activate/deactivate, or replace/remove the image. Bracket and type are fixed (they are part of the id)."""
    task = db.get(AssessmentTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    _validate_task_fields(None, None, max_seconds)
    image_data = await _read_task_image(image) if image is not None and image.filename else None

    if title is not None:
        task.title = title.strip()
    if instructions is not None:
        task.instructions = instructions.strip()
    if content_text is not None:
        task.content_text = content_text.strip()
    if max_seconds is not None:
        task.max_seconds = max_seconds
    if keywords is not None:
        task.keywords = _parse_keywords(keywords)
    if visual_json is not None:
        task.visual_json = _parse_visual(visual_json)
    if is_active is not None:
        task.is_active = is_active
    if remove_image:
        _delete_task_image(task)
    if image_data:
        _save_task_image(task, *image_data)
    db.commit()
    return _admin_task_out(task, str(request.base_url), _attempts_by_task(db, [task.id]).get(task.id, 0))


# ============================================================================= admin: patient directory & history
def _admin_patient_row(p: Patient, sessions: list[ScreeningSession]) -> AdminPatientRow:
    age = age_from_dob(p.date_of_birth)
    b = bracket_for_age(age)
    latest = max(sessions, key=lambda s: as_utc(s.created_at)) if sessions else None
    indicator = json.loads(latest.summary_json)["screening_indicator"] if latest else None
    return AdminPatientRow(
        id=p.id, full_name=p.full_name, age=age, age_bracket=bracket_info(b) if b else None, registered_at=p.created_at,
        owner_name=p.owner.full_name, owner_email=p.owner.email, owner_role=p.owner.role,
        total_sessions=len(sessions), last_session_at=latest.created_at if latest else None,
        latest_severity_hint=indicator["severity_hint"] if indicator else None,
        latest_label=indicator["label"] if indicator else None,
        latest_overall_score=latest.overall_speech_score if latest else None,
    )


def _sessions_by_patient(db: Session, patient_ids: list[str] | None = None) -> dict[str, list[ScreeningSession]]:
    q = select(ScreeningSession)
    if patient_ids is not None:
        q = q.where(ScreeningSession.patient_id.in_(patient_ids))
    out: dict[str, list[ScreeningSession]] = {}
    for s in db.scalars(q).all():
        out.setdefault(s.patient_id, []).append(s)
    return out


def _admin_sessions(db: Session, patient: Patient, sessions: list[ScreeningSession]) -> list[AdminSessionRow]:
    rows = []
    for s in sorted(sessions, key=lambda x: as_utc(x.created_at), reverse=True):
        summary = json.loads(s.summary_json)
        analyses = db.scalars(
            select(Analysis).where(Analysis.session_id == s.id, Analysis.patient_id == patient.id).order_by(Analysis.created_at)
        ).all()
        titles = _task_titles(db, [a.task_id for a in analyses])
        recordings = []
        for a in analyses:
            features = json.loads(a.result_json).get("acoustic_features", {})
            recordings.append(AdminRecording(
                analysis_id=a.id, task_type=a.task_type, task_id=a.task_id, title=titles.get(a.task_id, a.task_type.title()),
                created_at=a.created_at, overall_confidence_percent=a.overall_confidence_percent,
                overall_speech_score=a.overall_speech_score, duration_sec=float(features.get("duration_sec", 0.0)),
            ))
        rows.append(AdminSessionRow(
            session_id=s.id, created_at=s.created_at, recording_count=s.recording_count,
            overall_speech_score=s.overall_speech_score, overall_confidence_percent=s.overall_confidence_percent,
            severity_hint=summary["screening_indicator"]["severity_hint"], label=summary["screening_indicator"]["label"],
            recordings=recordings,
        ))
    return rows


@app.get("/api/v1/admin/patients", response_model=list[AdminPatientRow], tags=["admin"])
def admin_patients(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Patient directory: every registered patient with session count and latest screening risk."""
    patients = db.scalars(select(Patient).order_by(Patient.full_name)).all()
    by_patient = _sessions_by_patient(db)
    return [_admin_patient_row(p, by_patient.get(p.id, [])) for p in patients]


def _admin_get_patient(db: Session, patient_id: str) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/api/v1/admin/patients/{patient_id}", response_model=AdminPatientProfile, tags=["admin"])
def admin_patient_profile(patient_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Patient profile + chronological session history (newest first)."""
    patient = _admin_get_patient(db, patient_id)
    sessions = _sessions_by_patient(db, [patient.id]).get(patient.id, [])
    return AdminPatientProfile(
        patient=_admin_patient_row(patient, sessions), date_of_birth=patient.date_of_birth, is_self=patient.is_self,
        sessions=_admin_sessions(db, patient, sessions),
    )


@app.get("/api/v1/admin/patients/{patient_id}/sessions", response_model=list[AdminSessionRow], tags=["admin"])
def admin_patient_sessions(patient_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    patient = _admin_get_patient(db, patient_id)
    return _admin_sessions(db, patient, _sessions_by_patient(db, [patient.id]).get(patient.id, []))


# ============================================================================= WebSocket (Component 4)
def _ws_user_ok(token: str | None) -> bool:
    if not token:
        return False
    user_id = decode_token(token)
    if user_id is None:
        return False
    with SessionLocal() as db:
        return db.get(User, user_id) is not None


@app.websocket("/ws/therapy/{session_id}")
async def therapy_stream(ws: WebSocket, session_id: str, token: str | None = Query(None)):
    if not _ws_user_ok(token):
        await ws.close(code=1008)
        return
    await ws.accept()
    sample_rate = settings.stream_sample_rate
    seq = 0
    await ws.send_json({
        "type": "ready",
        "session_id": session_id,
        "expected_encoding": "pcm_s16le",
        "sample_rate": sample_rate,
        "max_chunk_ms": settings.stream_max_chunk_ms,
    })
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                t0 = time.perf_counter()
                chunk = message["bytes"]
                if len(chunk) % 2:
                    chunk = chunk[:-1]
                pcm = np.frombuffer(chunk, dtype=np.int16)
                seq += 1
                meta = {"seq": seq, "server_ts": int(time.time() * 1000), **chunk_metrics(pcm, sample_rate)}
                await hub.forward(session_id, meta, chunk)
                meta["processing_ms"] = round((time.perf_counter() - t0) * 1000, 3)
                meta["within_budget"] = meta["chunk_ms"] <= settings.stream_max_chunk_ms
                meta["listeners"] = hub.listener_count(session_id)
                await ws.send_json({"type": "chunk_ack", **meta})

            elif message.get("text"):
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "detail": "Invalid JSON"})
                    continue
                if data.get("type") == "config":
                    sample_rate = int(data.get("sample_rate", sample_rate))
                    await ws.send_json({"type": "config_ack", "sample_rate": sample_rate})
                elif data.get("type") == "ping":
                    await ws.send_json({"type": "pong", "client_ts": data.get("client_ts"), "server_ts": int(time.time() * 1000)})
    except (WebSocketDisconnect, RuntimeError):
        pass


@app.websocket("/ws/therapy/{session_id}/listen")
async def therapy_listen(ws: WebSocket, session_id: str, token: str | None = Query(None)):
    """Component 4 back-end subscribes here to receive the live chunks of a session."""
    if not _ws_user_ok(token):
        await ws.close(code=1008)
        return
    await ws.accept()
    await hub.add_listener(session_id, ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; messages from listeners are ignored
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await hub.remove_listener(session_id, ws)
