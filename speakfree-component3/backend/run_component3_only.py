"""
run_component3_only.py  (OPTIONAL launcher)
==========================================

Serves ONLY the Component 3 API, reusing the exact same router that main.py
registers (`routes.component3_routes.router`). No Component 3 logic is
duplicated here.

Use this when you want to demo Component 3 WITHOUT installing Component 2's
heavy audio stack (openai-whisper / torch / librosa). For the full chained
demo (Component 2 upload -> Component 3) run the normal combined server
instead:

    uvicorn main:app --port 8000

Run this one with:

    python run_component3_only.py
    # -> http://127.0.0.1:8000/docs   (Component 3 endpoints only)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import component3_routes

app = FastAPI(title="SpeakFree API - Component 3 only")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(component3_routes.router, prefix="/api/v1", tags=["Component 3"])


@app.get("/")
def home():
    return {
        "message": "SpeakFree Component 3 API (standalone launcher)",
        "docs": "http://127.0.0.1:8000/docs",
        "analyze": "POST /api/v1/component3/analyze",
        "health": "GET /api/v1/component3/health",
        "note": "For the full Component 2 -> Component 3 demo run: uvicorn main:app --port 8000",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
