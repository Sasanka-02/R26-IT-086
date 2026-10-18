"""
Database models (SQLAlchemy 2.x).
SQLite is used for local development; switch DATABASE_URL to PostgreSQL for deployment.
Every column type used here is portable between the two (no SQLite-only features).

Schema changes are managed with Alembic (backend/migrations). Run `alembic upgrade head`,
or let the app do it at startup (AUTO_MIGRATE=true).

Privacy note: raw audio is NEVER stored. Only derived results (JSON) are persisted.
"""
import os
import secrets
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config import settings

TASK_TYPES = ("reading", "picture", "scenario", "questions")
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def make_engine(url: str):
    """Create an engine; SQLite gets thread-safety off and foreign keys ON (PostgreSQL behaviour)."""
    is_sqlite = url.startswith("sqlite")
    eng = create_engine(url, connect_args={"check_same_thread": False} if is_sqlite else {}, pool_pre_ping=True)
    if is_sqlite:
        @event.listens_for(eng, "connect")
        def _sqlite_fk_on(dbapi_conn, _record):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return eng


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for timezone=True columns; treat them as UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def new_patient_id() -> str:
    return "SF-" + secrets.token_hex(4).upper()


class Base(DeclarativeBase):
    # Deterministic constraint names, so Alembic migrations work the same on SQLite and PostgreSQL.
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # patient | guardian | clinician
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # ---- login verification (brute-force protection) ----
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patients: Mapped[list["Patient"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Patient(Base):
    """
    A person being screened / practising. Patients own themselves; guardians/clinicians own others.

    Age: from date_of_birth when known, otherwise the `age` entered at sign-up (or on the one-time
    "How old are you?" screen). age_bracket (1–8, age_brackets.py) is saved with it; a therapist
    can pin the practice bracket (age_bracket_override) and assign exercises (C4 therapy plan).
    """

    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("age IS NULL OR age BETWEEN 6 AND 100", name="age_range"),
        CheckConstraint("age_bracket IS NULL OR age_bracket BETWEEN 1 AND 8", name="age_bracket_range"),
        CheckConstraint("age_bracket_override IS NULL OR age_bracket_override BETWEEN 1 AND 8", name="age_bracket_override_range"),
    )

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=new_patient_id)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_bracket: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_bracket_override: Mapped[int | None] = mapped_column(Integer, nullable=True)   # set by a therapist
    assigned_exercises: Mapped[list | None] = mapped_column(JSON, nullable=True)       # set by a therapist
    guardian_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # under 18
    notes_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # therapist notes seen
    daf_delay_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)           # DAF calibration result
    is_self: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="patients")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    attempts: Mapped[list["TaskAttempt"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class AssessmentTask(Base):
    """
    One clinical task in the task library, delivered by age bracket.

    content_text holds the reading passage (reading), the picture caption (picture),
    the scenario prompt (scenario) or the question (questions).
    """

    __tablename__ = "assessment_tasks"
    __table_args__ = (
        CheckConstraint("age_bracket BETWEEN 1 AND 7", name="age_bracket_range"),
        CheckConstraint("task_type IN ('reading', 'picture', 'scenario', 'questions')", name="task_type_valid"),
        CheckConstraint("max_seconds > 0", name="max_seconds_positive"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "b2-pic-1"
    age_bracket: Mapped[int] = mapped_column(Integer, index=True)
    task_type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(200))
    instructions: Mapped[str] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)  # relative to STATIC_DIR, e.g. "tasks/b2-pic-1.png"
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    visual_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # emoji/chart fallback when there is no image
    max_seconds: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Analysis(Base):
    """One analysed task recording (picture / scenario / question / reading)."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(20))
    task_id: Mapped[str] = mapped_column(ForeignKey("assessment_tasks.id"), index=True)
    age_bracket: Mapped[int] = mapped_column(Integer)
    overall_speech_score: Mapped[float] = mapped_column(Float)
    overall_confidence_percent: Mapped[float] = mapped_column(Float)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="analyses")
    task: Mapped[AssessmentTask] = relationship()


class TaskAttempt(Base):
    """A patient attempted a task (one row per analysed recording). Drives task rotation."""

    __tablename__ = "task_attempts"
    __table_args__ = (Index("ix_task_attempts_patient_task", "patient_id", "task_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("assessment_tasks.id"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="attempts")


class ScreeningSession(Base):
    """Aggregated Component 1 output for one completed screening session (all task recordings)."""

    __tablename__ = "screening_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    age_bracket: Mapped[int] = mapped_column(Integer)
    recording_count: Mapped[int] = mapped_column(Integer)
    overall_speech_score: Mapped[float] = mapped_column(Float)
    overall_confidence_percent: Mapped[float] = mapped_column(Float)
    summary_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship()


def run_migrations(database_url: str | None = None) -> None:
    """Upgrade the database to the latest Alembic revision (same as `alembic upgrade head`)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url or settings.database_url)
    command.upgrade(cfg, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================= integrated pipeline (C2 → C3 → C4)
class PipelineRun(Base):
    """
    One run of the backend pipeline for a finalised screening session:
    C1 session summary → C2 articulation report → C3 severity report → C4 therapy profile.
    Visible only to the admin; patients see the C1 results page and their therapy plan.
    """

    __tablename__ = "pipeline_runs"

    session_id: Mapped[str] = mapped_column(ForeignKey("screening_sessions.id", ondelete="CASCADE"), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))  # completed | partial | failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    articulation_score: Mapped[float | None] = mapped_column(Float, nullable=True)      # C2
    primary_disorder: Mapped[str | None] = mapped_column(String(20), nullable=True)     # C3
    severity_level: Mapped[int | None] = mapped_column(Integer, nullable=True)          # C3
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)           # C3
    therapy_focus: Mapped[str | None] = mapped_column(String(20), nullable=True)        # C4
    c2_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    c3_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_timings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship()


class TherapyProfile(Base):
    """C4 therapy profile created from one pipeline run. The newest row per patient is active."""

    __tablename__ = "therapy_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("screening_sessions.id", ondelete="CASCADE"), index=True)
    focus: Mapped[str] = mapped_column(String(20))
    severity_level: Mapped[int] = mapped_column(Integer)
    profile_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TherapyAttempt(Base):
    """One completed therapy exercise (numbers only - never audio)."""

    __tablename__ = "therapy_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(60))
    exercise_type: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    record_json: Mapped[str] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssistantMessage(Base):
    """AI assistant chat log (for the admin's therapy monitor)."""

    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    reply: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20))  # classifier | llm | fallback
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TherapyGoal(Base):
    """A measurable goal a therapist sets on top of the plan's automatic goals (component4/therapist.py)."""

    __tablename__ = "therapy_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(40))  # average_score | sessions_per_week | long_pauses_per_exercise
    target: Mapped[float] = mapped_column(Float)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TherapyNote(Base):
    """A clinical note. Shared notes are shown to the patient (new until read); private ones only to therapists."""

    __tablename__ = "therapy_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_name: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    shared: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TherapyHomework(Base):
    """Due date and number of attempts for an exercise in Patient.assigned_exercises."""

    __tablename__ = "therapy_homework"
    __table_args__ = (
        Index("ix_therapy_homework_patient_exercise", "patient_id", "exercise_id", unique=True),
        CheckConstraint("times BETWEEN 1 AND 20", name="times_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(String(60))
    due: Mapped[date | None] = mapped_column(Date, nullable=True)
    times: Mapped[int] = mapped_column(Integer, default=1)
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttemptRating(Base):
    """A therapist's 1-5 rating of one therapy attempt (expert validation of the practice score)."""

    __tablename__ = "therapy_attempt_ratings"
    __table_args__ = (
        Index("ix_therapy_attempt_ratings_attempt_rater", "attempt_id", "rater_user_id", unique=True),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("therapy_attempts.id", ondelete="CASCADE"), index=True)
    rater_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rater: Mapped[User] = relationship()


class PlanReview(Base):
    """A therapist's verdict on a generated plan, stored with the plan exactly as it was seen."""

    __tablename__ = "therapy_plan_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verdict: Mapped[str] = mapped_column(String(20))  # appropriate | partly | not_appropriate
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsabilitySurvey(Base):
    """One System Usability Scale response per account (a repeat replaces the earlier one)."""

    __tablename__ = "usability_surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PrivacyLedgerEntry(Base):
    """ε spent by one differentially private release (cohort report), for the privacy budget."""

    __tablename__ = "privacy_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[str] = mapped_column(String(40), index=True)   # e.g. "cohort-report"
    release_key: Mapped[str] = mapped_column(String(80), unique=True)  # data fingerprint + ε (no double spending)
    epsilon: Mapped[float] = mapped_column(Float)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppointmentRequest(Base):
    """A patient / guardian asks for a session with a speech-language pathologist; the admin confirms it."""

    __tablename__ = "appointment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    preferred_date: Mapped[date] = mapped_column(Date)
    preferred_time: Mapped[str] = mapped_column(String(20))      # morning | afternoon | evening
    mode: Mapped[str] = mapped_column(String(20))                # online | in_person
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | confirmed | declined | cancelled
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship()
    user: Mapped[User] = relationship()
