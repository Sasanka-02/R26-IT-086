import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from services.component1_pipeline import build_component3_payload, process_component1_output
from services.component2_service import analyze_articulation
from services.component3_client import send_to_component3

logger = logging.getLogger(__name__)
router = APIRouter()
UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
WHISPER_MODEL_NAME = os.getenv("SPEAKFREE_WHISPER_MODEL", "tiny.en")


class Component1Output(BaseModel):
    """Component 1's AnalyzeResponse (schema 1.x); only the session fields are required."""
    model_config = ConfigDict(extra="allow")

    schema_version: Optional[str] = None
    analysis_id: Optional[str] = None
    session_id: str
    patient_id: Optional[str] = None
    age_bracket: Optional[int | str] = None
    task_type: str
    reference_text: Optional[str] = None
    transcript: Optional[str] = None
    word_segments: list[dict] = []
    overall_confidence_percent: Optional[float] = None
    dysfluency_threshold: Optional[float] = None
    wer: Optional[dict] = None
    acoustic_features: Optional[dict] = None


def _parse_component1(data) -> dict:
    """Accepts Component 1's JSON directly, or wrapped as {"component1_output": {...}}."""
    if isinstance(data, dict) and isinstance(data.get("component1_output"), dict):
        data = data["component1_output"]
    try:
        return Component1Output.model_validate(data).model_dump()
    except ValidationError as exc:
        raise HTTPException(422, f"Invalid Component 1 JSON: {exc}") from exc


def _deliver(result: dict) -> dict:
    payload = result.get("component3_input")
    result["component3_delivery"] = (
        send_to_component3(payload) if payload
        else {"status": "not_sent", "message": "No articulation score was produced."}
    )
    return result


@asynccontextmanager
async def _saved_upload(file: UploadFile):
    original_name = Path(file.filename or "audio").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio type. Upload WAV, MP3, M4A, FLAC or OGG.")
    content = await file.read()
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File exceeds the 25 MB prototype limit.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    temp_path.write_bytes(content)
    try:
        yield temp_path, original_name
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove temporary audio file %s", temp_path.name)


async def _run(func, *args, **kwargs):
    try:
        return await run_in_threadpool(func, *args, **kwargs)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Component 2 analysis failed")
        raise HTTPException(500, "Analysis failed. Check the backend terminal for details.") from exc


@router.post("/component2/from-component1")
async def score_from_component1(component1_json: dict = Body(...)):
    """Main pipeline: Component 1 JSON -> articulation score -> sent to Component 3."""
    component1 = _parse_component1(component1_json)
    result = await _run(process_component1_output, component1)
    return await run_in_threadpool(_deliver, result)


@router.post("/component2/from-component1-audio")
async def score_from_component1_with_audio(
    component1_json: str = Form(...),
    file: UploadFile = File(...),
    target_text: Optional[str] = Form(None),
):
    """Component 1 JSON plus the session recording: phoneme-level PCC-R is sent to Component 3."""
    try:
        component1 = _parse_component1(json.loads(component1_json))
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"Invalid Component 1 JSON: {exc}") from exc
    target = target_text or component1.get("reference_text")
    async with _saved_upload(file) as (path, _):
        analysis = await _run(analyze_articulation, str(path), WHISPER_MODEL_NAME, target, component1)
    result = await _run(process_component1_output, component1, analysis)
    return await run_in_threadpool(_deliver, result)


async def _analyse_audio(file: UploadFile, target_text: Optional[str]):
    async with _saved_upload(file) as (path, original_name):
        result = await _run(analyze_articulation, str(path), WHISPER_MODEL_NAME, target_text)
    result["uploaded_filename"] = original_name
    payload = build_component3_payload(None, result["articulation_analysis"])
    return {
        "message": "Audio analysis completed.",
        "filename": original_name,
        "component": "Component 2 - Alignment and Articulation Analytics",
        "component2_output": result,
        "ready_for_component3": payload is not None,
        "component3_input": payload,
    }


@router.post("/component2/analyze")
async def analyze_component2(file: UploadFile = File(...), target_text: Optional[str] = Form(None)):
    """PCC articulation score from a recording alone; not sent to Component 3 (no session id)."""
    return await _analyse_audio(file, target_text)


@router.post("/audio")
async def upload_audio_old(file: UploadFile = File(...), target_text: Optional[str] = Form(None)):
    return await _analyse_audio(file, target_text)
