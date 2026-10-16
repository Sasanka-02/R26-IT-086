from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload_routes

app = FastAPI(title="SpeakFree API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_routes.router, prefix="/api/v1", tags=["Component 2"])

# ---------------------------------------------------------------------------
# Component 3 - Multi-Disorder Severity Classification & Risk Prediction
# (I.L.S. Tharushan - IT21315114). Isolated module; consumes Component 2
# output. Wrapped so a Component 3 import error can never break Component 2.
# ---------------------------------------------------------------------------
try:
    from routes import component3_routes

    app.include_router(
        component3_routes.router, prefix="/api/v1", tags=["Component 3"]
    )
    _COMPONENT3_LOADED = True
except Exception as _c3_exc:  # pragma: no cover - defensive
    _COMPONENT3_LOADED = False
    print(f"[main] Component 3 routes not loaded: {_c3_exc!r}")


@app.get("/")
def home():
    return {
        "message": "SpeakFree backend is running",
        "api_docs": "http://localhost:8000/docs",
        "component2_endpoint": "/api/v1/component2/analyze",
        "component3_endpoint": (
            "/api/v1/component3/analyze" if _COMPONENT3_LOADED else "unavailable"
        ),
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }