import logging
import os

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.model_loader import models_ready
from app.schemas.response import ExtractFeaturesResponse, HealthResponse
from app.services.audio_preprocessor import preprocess_audio
from app.services.feature_extractor import extract_all_features
from app.utils.file_utils import cleanup_file, save_upload

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    status = models_ready()
    return HealthResponse(status="ok", **status)


@router.post("/api/v1/extract-features", response_model=ExtractFeaturesResponse)
async def extract_features_endpoint(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    task_type: str = Form(...),
    session_id: str = Form(...),
    age_category: str = Form("adults"),
):
    settings = get_settings()

    raw_content_type = audio_file.content_type or ""
    content_type = raw_content_type.split(";")[0].strip().lower()
    logger.info(
        "Received upload: filename=%s raw_content_type=%r parsed=%r",
        audio_file.filename,
        raw_content_type,
        content_type,
    )

    if content_type not in settings.allowed_mime_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type '{raw_content_type}'. "
            f"Allowed: {settings.allowed_mime_types}",
        )

    raw_path = await save_upload(audio_file, settings.upload_dir)

    size_mb = os.path.getsize(raw_path) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        cleanup_file(raw_path)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max is {settings.max_upload_mb}MB.",
        )

    wav_path = os.path.join(
        settings.processed_dir, os.path.basename(raw_path) + ".wav"
    )

    try:
        if settings.use_celery:
            from worker.tasks import run_feature_extraction

            result_dict = run_feature_extraction(raw_path, wav_path, task_type, session_id)
        else:
            preprocessed = preprocess_audio(raw_path, wav_path)
            result_dict = extract_all_features(
                wav_path=preprocessed["wav_path"],
                samples=preprocessed["samples"],
                sample_rate=preprocessed["sample_rate"],
                duration_seconds=preprocessed["duration_seconds"],
                snr_db=preprocessed["snr_db"],
            )

        result_dict["session_id"] = session_id
        result_dict["task_type"] = task_type

        return ExtractFeaturesResponse(**result_dict)

    except Exception:
        logger.exception("Feature extraction failed for session %s", session_id)
        raise HTTPException(
            status_code=500,
            detail="Feature extraction failed. Please try recording again.",
        )
    finally:
        background_tasks.add_task(cleanup_file, raw_path)
        background_tasks.add_task(cleanup_file, wav_path)