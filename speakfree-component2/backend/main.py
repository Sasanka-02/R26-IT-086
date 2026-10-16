from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload_routes

app = FastAPI(
    title="SpeakFree API",
    description=(
        "Component 2 articulation analysis: articulation score from Component 1's JSON "
        "(or PCC-R when the recording is supplied), sent to Component 3."
    ),
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(upload_routes.router, prefix="/api/v1", tags=["Component 2"])


@app.get("/")
def home():
    return {
        "message": "SpeakFree backend is running",
        "api_docs": "http://localhost:8000/docs",
        "component1_json_endpoint": "/api/v1/component2/from-component1",
        "component1_with_audio_endpoint": "/api/v1/component2/from-component1-audio",
        "audio_analysis_endpoint": "/api/v1/component2/analyze",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
