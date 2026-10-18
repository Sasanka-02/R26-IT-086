"""
SpeakFree – Component 1 (Noise-Robust Speech Screening & Feature Extraction)
Central configuration. Every value can be overridden in backend/.env
"""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "SpeakFree - Integrated Speech Screening & Therapy Platform (C1-C4)"
    # 1.1.0: task_type "questions", model.rejected_segments, session summary
    # 1.2.0: model_features.acoustic_biomarker_windows (TORGO features for Component 3)
    schema_version: str = "1.2.0"

    # ---- Persistence (SQLite by default, PostgreSQL in production) ----
    # PostgreSQL example: postgresql+psycopg://user:pass@localhost:5432/speakfree  (pip install "psycopg[binary]")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./speakfree_c1.db")
    # Run `alembic upgrade head` automatically when the API starts.
    auto_migrate: bool = _bool("AUTO_MIGRATE", True)

    # ---- Auth ----
    jwt_secret: str = os.getenv("JWT_SECRET", "CHANGE-ME-speakfree-dev-secret")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    # Login verification: lock the account for LOCKOUT_MINUTES after MAX_FAILED_LOGINS wrong passwords.
    max_failed_logins: int = int(os.getenv("MAX_FAILED_LOGINS", "5"))
    lockout_minutes: int = int(os.getenv("LOCKOUT_MINUTES", "15"))
    # Built-in administrator (role "admin"): sees every patient and the technical session dashboards.
    # Credentials are hardcoded as requested; the account is created/updated at startup (main.ensure_admin).
    # Change them here before any real deployment.
    admin_email: str = "admin@speakfree.lk"
    admin_password: str = "SpeakFree@Admin2026"
    admin_name: str = "SpeakFree Admin"

    # ---- Static files (task images, served at /static) ----
    static_dir: str = os.getenv("STATIC_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))
    max_image_mb: int = int(os.getenv("MAX_IMAGE_MB", "5"))
    max_video_mb: int = int(os.getenv("MAX_VIDEO_MB", "25"))  # short scenario videos (.mp4 / .webm)

    # ---- CORS (React dev server) ----
    cors_origins: list[str] = field(
        default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )

    # ---- Whisper ASR ----
    # tiny.en | base.en | small.en | medium.en  (".en" models are English-only and more accurate for English)
    whisper_model: str = os.getenv("WHISPER_MODEL", "base.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "auto")  # auto | cpu | cuda
    # Whisper normally "cleans up" fillers (um, uh, repetitions). A verbatim-style
    # initial prompt nudges it to keep them, which matters for dysfluency screening.
    verbatim_prompt: str = os.getenv(
        "VERBATIM_PROMPT",
        "Umm, let me think like, hmm... Okay, here's what I'm, like, thinking.",
    )

    # ---- Clinical thresholds ----
    dysfluency_threshold: float = float(os.getenv("DYSFLUENCY_THRESHOLD", "0.60"))  # C_word < 0.60
    high_confidence_threshold: float = 0.90
    # Hallucination guard (asr_service.segment_rejection_reason): Whisper segments judged to be
    # non-speech, or impossible repetition loops, are excluded before Eq. 1–3.
    no_speech_threshold: float = float(os.getenv("NO_SPEECH_THRESHOLD", "0.75"))
    max_words_per_sec: float = float(os.getenv("MAX_WORDS_PER_SEC", "8.0"))
    significant_pause_sec: float = 0.25  # pauses > 250 ms are clinically significant

    # ---- Pre-processing / features ----
    enable_noise_reduction: bool = _bool("ENABLE_NOISE_REDUCTION", True)
    # Voice activity detection: silero (neural, noise-robust) | energy (adaptive threshold). Falls back to energy.
    vad_backend: str = os.getenv("VAD_BACKEND", "silero").strip().lower()
    enable_hubert: bool = _bool("ENABLE_HUBERT", False)
    hubert_model: str = os.getenv("HUBERT_MODEL", "facebook/hubert-base-ls960")

    # ---- Integration (Components 2-4) ----
    # TORGO-style acoustic windows computed while the audio is in memory (Component 3 stage 1).
    enable_acoustic_biomarkers: bool = _bool("ENABLE_ACOUSTIC_BIOMARKERS", True)
    # Run C2 -> C3 -> C4 automatically when a screening session is finalised.
    run_pipeline_on_finalize: bool = _bool("RUN_PIPELINE_ON_FINALIZE", True)

    # ---- Upload limits ----
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))

    # ---- Streaming (Component 4 contract) ----
    stream_sample_rate: int = 16000
    stream_max_chunk_ms: int = 300


settings = Settings()
