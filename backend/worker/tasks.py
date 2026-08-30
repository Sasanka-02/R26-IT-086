from app.core.celery_app import celery_app
from app.services.audio_preprocessor import preprocess_audio
from app.services.feature_extractor import extract_all_features


@celery_app.task(name="worker.tasks.run_feature_extraction")
def run_feature_extraction(raw_path: str, wav_path: str, task_type: str, session_id: str) -> dict:
    """
    Celery-wrapped version of the same synchronous pipeline used inline in
    endpoints.py. Enable by setting USE_CELERY=true and calling
    `run_feature_extraction.delay(...)` from the endpoint instead of the
    direct function call, then have the frontend poll a
    GET /api/v1/results/{task_id} endpoint (not yet implemented — add once
    the frontend supports async job polling).
    """
    preprocessed = preprocess_audio(raw_path, wav_path)
    result = extract_all_features(
        wav_path=preprocessed["wav_path"],
        samples=preprocessed["samples"],
        sample_rate=preprocessed["sample_rate"],
        duration_seconds=preprocessed["duration_seconds"],
        snr_db=preprocessed["snr_db"],
    )
    result["session_id"] = session_id
    result["task_type"] = task_type
    return result
