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
    """A person being screened. Patients own themselves; guardians/clinicians own others."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=new_patient_id)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date] = mapped_column(Date)
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
