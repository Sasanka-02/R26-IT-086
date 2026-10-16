from pathlib import Path
import shutil
import uuid

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Form,
)

from services.component2_service import (
    analyze_articulation
)


router = APIRouter()


# =========================================================
# Configuration
# =========================================================

UPLOAD_DIR = Path(
    "uploads"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


ALLOWED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
}


# =========================================================
# Component 2 endpoint
# =========================================================

@router.post(
    "/component2/analyze"
)
async def analyze_component2(
    file: UploadFile = File(...),
    reference_text: str = Form("")
):

    # -----------------------------------------------------
    # Validate filename
    # -----------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    # -----------------------------------------------------
    # Validate extension
    # -----------------------------------------------------

    extension = (
        Path(
            file.filename
        ).suffix
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid file type. "
                "Only .wav, .mp3 and .m4a "
                "audio files are supported."
            )
        )

    # -----------------------------------------------------
    # Safe temporary filename
    # -----------------------------------------------------

    safe_filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = (
        UPLOAD_DIR
        / safe_filename
    )

    try:

        # -------------------------------------------------
        # Save uploaded file
        # -------------------------------------------------

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        # -------------------------------------------------
        # Component 2 analysis
        # -------------------------------------------------

        component2_output = (
            analyze_articulation(
                audio_path=
                    str(
                        file_path
                    ),

                reference_text=
                    reference_text.strip()
            )
        )

        # -------------------------------------------------
        # API response
        # -------------------------------------------------

        return {

            "message":
                "Component 2 analysis completed",

            "filename":
                file.filename,

            "component":
                (
                    "Component 2 - "
                    "Alignment and Articulation Analytics"
                ),

            "component2_output":
                component2_output,

            "ready_for_component3":
                True,

            "component3_input":
                component2_output[
                    "component3_ready_output"
                ]
        }

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        # -------------------------------------------------
        # Delete temporary uploaded file
        # -------------------------------------------------

        if file_path.exists():

            try:

                file_path.unlink()

            except OSError:

                pass


# =========================================================
# Backward-compatible endpoint
# =========================================================

@router.post(
    "/audio"
)
async def upload_audio_old(
    file: UploadFile = File(...)
):

    return await analyze_component2(
        file=file,
        reference_text=""
    )