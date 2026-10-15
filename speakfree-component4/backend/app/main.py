import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.therapy.router import router as therapy_router
from app.therapy.simulation import evaluate
from app.therapy.therapist_router import router as therapist_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(therapy_router)
app.include_router(therapist_router)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "component": "4 — Therapy Assistant"}


@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s", settings.app_name)
    # The planner simulation for the evidence page is deterministic and cached;
    # compute it in the background so the page doesn't wait for it.
    threading.Thread(target=evaluate, daemon=True).start()
