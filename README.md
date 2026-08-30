# SpeakFree — Component 1

Frontend speech capture + noise-robust feature extraction pipeline for the
R26-IT-086 speech disorder screening platform.

## Structure

- `frontend/` — React + Vite + TypeScript capture UI (3 elicitation tasks)
- `backend/` — FastAPI service (Whisper + HuBERT + Librosa feature extraction)

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

First run downloads the Whisper and HuBERT model weights — this can take a
few minutes. Use `WHISPER_MODEL_SIZE=tiny` in `.env` for faster local
iteration; switch to `small`/`medium` for real evaluation runs.

Check it's alive:
```bash
curl http://localhost:8000/api/v1/health
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

### 3. Add stimuli

Drop a picture into `frontend/public/stimuli/images/picture-1.jpg` and a
short silent video into `frontend/public/stimuli/videos/clip-1.mp4` — the
app references these paths directly.

### 4. (Optional) Async processing with Celery + Redis

```bash
cd backend
docker compose up --build
```
This starts Redis, the FastAPI API, and a Celery worker together. Set
`USE_CELERY=true` in `.env` once you wire the endpoint to call
`run_feature_extraction.delay(...)` instead of the inline synchronous call
(see the comment in `worker/tasks.py`).

## Running tests

```bash
cd backend
pytest
```

## Notes on scope

This component owns: browser-based multi-task audio capture (picture
description, video description, AI-guided conversation), noise reduction,
VAD-based silence trimming (long pauses preserved, not stripped), Whisper
confidence-scored ASR, HuBERT frame embeddings, and Librosa acoustic
metrics — packaged into the structured JSON contract in
`backend/app/schemas/response.py` for the other three components
(articulation analysis, severity classification, therapy delivery) to
consume.
