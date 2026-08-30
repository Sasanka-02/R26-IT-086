from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SpeakFree Component 1 — Feature Extraction API"
    upload_dir: str = "storage/uploads"
    processed_dir: str = "storage/processed"

    whisper_model_size: str = "small"  # "tiny" for faster local dev
    hubert_model_name: str = "facebook/hubert-base-ls960"

    low_confidence_threshold: float = 0.60

    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False  # False => runs extraction as a FastAPI background task

    max_upload_mb: int = 25
    allowed_mime_types: tuple[str, ...] = (
        "audio/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/ogg",
    )

    cors_origins: tuple[str, ...] = ("http://localhost:5173",)


@lru_cache
def get_settings() -> Settings:
    return Settings()
