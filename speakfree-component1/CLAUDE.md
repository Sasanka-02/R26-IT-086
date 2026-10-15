# SpeakFree – Component 1 (R26-IT-086, SLIIT)
Noise-Robust Speech Screening & Feature Extraction.
FastAPI backend + React/Vite/Tailwind frontend. Owner of the build: E.Y. Randiw.

## Environment
- Windows, PowerShell, Python 3.11 venv at backend/venv, Node 20+, FFmpeg on PATH
- Backend:  `cd backend; .\venv\Scripts\Activate.ps1; uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3`
- Tests:    `cd backend; python -m pytest -q`
- Frontend: `cd frontend; npm run dev`   (typecheck: `npm run typecheck`)

## Core novelty – keep intact
- backend/asr_service.py implements the ASR-confidence biomarker:
  Eq.1 P(t_i) = exp(logprob_i)
  Eq.2 C_word = (1/k) Σ exp(logprob_i)        → dysfluency candidate if C_word < 0.60
  Eq.3 C_overall = ((1/N) Σ exp(logprob_i)) × 100
- Never change these formulas and keep the math comment blocks above each equation.
- If the ASR model is swapped or fine-tuned, it must still expose per-token log-probabilities
  so Eq.1–3 keep working.

## Models – any model may be used, trained or fine-tuned
You may use, download, train or fine-tune ANY model needed to complete Component 1, for example:
- ASR: Whisper (any size), faster-whisper, wav2vec2, or Whisper fine-tuned on disordered/child speech
- Self-supervised embeddings: HuBERT, wav2vec2, WavLM
- Noise reduction / VAD: Silero VAD, webrtcvad, DeepFilterNet, RNNoise, noisereduce
- Dysfluency classifiers: e.g. a model trained on SEP-28k, FluencyBank or UCLASS to detect
  blocks, prolongations, repetitions and interjections (complements the confidence biomarker)
- Any scikit-learn / PyTorch model for fluency or quality scoring

Rules for training work:
- Put training code in `backend/training/` (scripts, configs, notebooks) and trained weights in
  `backend/models/` (git-ignored; add a download/README note instead of committing large files).
- Only use public research datasets or data with proper consent; record the dataset name,
  licence and split in `backend/training/README.md`.
- Use fixed random seeds, a held-out test set, and save metrics (accuracy, F1, WER, AUC as
  relevant) to `backend/training/results/` so they can be reported in the thesis/viva.
- Load trained models lazily (like WhisperConfidenceASR) and make them switchable via `.env`
  so the app still runs if a model file is missing (fall back to the pre-trained default).
- Prefer models that run on a normal laptop CPU at inference time; GPU only for training.
- Explain each new model's role in README.md (what it predicts, inputs, outputs, metrics).

## Other rules
- Raw audio must never be stored on the server – the temp file is deleted after analysis. Training data
  stays outside the app's runtime paths. Unfinished sessions may be kept only in the patient's own
  browser (IndexedDB, frontend/src/utils/recordingStore.ts) and are deleted once the session is analysed.
- Pauses > 250 ms are clinically significant; only trim leading/trailing silence.
- The /api/v1/analyze JSON (schemas.py AnalyzeResponse) is a contract for Components 2 and 3:
  add fields, never rename/remove them. Bump schema_version on changes. New model outputs go
  in new fields (e.g. `dysfluency_events`, `model_predictions`).
- Age brackets 6–20 (age_brackets.py and frontend/src/utils/age.ts must stay in sync).
- UI theme: light, from the SpeakFree mock-up (tokens in frontend/tailwind.config.js): canvas #F5F6FB,
  white cards, navy #1E3A8A (sidebar/brand), royal blue #1D4ED8 (buttons), lavender/violet #7C6CF0,
  amber #F59E0B ("Free" + notification dot).
- When fixing a file, show me the complete corrected file.
- Run pytest after backend changes and typecheck after frontend changes.

## 1. Database (SQLAlchemy 2.x, backend/database.py)
- Keep SQLite for development (DATABASE_URL in .env) but make everything PostgreSQL-compatible.
- users: add columns failed_logins (int, default 0), locked_until (datetime, nullable), last_login_at (datetime, nullable).
- NEW table assessment_tasks: id (string PK, e.g. "b2-pic-1"), age_bracket (int 1–7, indexed), task_type ("reading" | "picture" | "scenario", indexed), title, instructions, content_text (reading passage OR scenario prompt OR picture caption), image_path (nullable, relative path under static/tasks/), keywords (JSON list, for picture content coverage), visual_json (JSON, nullable – keeps the existing emoji/chart visual as fallback when no image), max_seconds (int), is_active (bool, default true), created_by_user_id (nullable FK users), created_at.
- NEW table task_attempts: id, patient_id (FK patients), task_id (FK assessment_tasks), analysis_id (FK analyses, nullable), attempted_at.
- analyses.task_id should reference assessment_tasks.id.
- Add Alembic for migrations (alembic init, first migration for the full schema) and document it in README. Tell me if I need to delete the old speakfree_c1.db.

## 2. Seed data (backend/seed.py)
- Idempotent script: insert every task from task_bank.py into assessment_tasks (skip ones that already exist).
- Add at least 2 more PICTURE and 2 more SCENARIO tasks per age bracket (original, age-appropriate content matching the bracket rules in CLAUDE.md / task_bank.py docstring) so tasks can rotate.
- Create backend/static/tasks/ with a README explaining image naming (<task_id>.png or .jpg). If an image file for a task exists, set image_path; otherwise keep visual_json fallback.
- Run with: python seed.py

## 3. Login verification (backend/auth.py + main.py)
- Keep bcrypt hashing and JWT (sub = user id, role, exp).
- Login: on wrong password increment failed_logins; after 5 failures set locked_until = now + 15 minutes and return 423 "Account locked, try again in N minutes". On success reset failed_logins, set last_login_at.
- Always return the same generic 401 message for unknown email or wrong password.
- Server-side validation on register: unique email, password ≥ 8 chars, DOB required for patient / child DOB for guardian, age must be 6–20.
- Keep the ownership check: a user can only access their own patients, tasks and results.

## 4. Age-based task delivery
- GET /api/v1/tasks?patient_id=...: compute age from DOB (today's date), map to bracket, then for each task_type select ONE active task for that bracket, preferring tasks this patient has NOT attempted (task_attempts); random among the least-attempted. Keep the response shape the frontend already uses ({patient_id, age, age_bracket, tasks:{reading, picture, scenario}}) and add image_url (absolute URL to /static/tasks/...) to picture tasks.
- Mount FastAPI StaticFiles at /static.
- POST /api/v1/analyze: load the task from the DB by task_id (reference text for WER, keywords for coverage), save analyses.task_id and insert a task_attempts row.
- Remove the in-memory TASK_BANK lookups from main.py (task_bank.py stays only as seed data).

## 5. Clinician task management
- Endpoints (role = clinician only, 403 otherwise): GET /api/v1/admin/tasks (filter by bracket/type), POST /api/v1/admin/tasks (multipart form + optional image upload, validate jpg/png/webp ≤ 5 MB, save to static/tasks/), PATCH /api/v1/admin/tasks/{id} (edit / activate / deactivate).
- Frontend: add a "Task Library" item in the sidebar, visible only to clinicians, with a page to list tasks by bracket and add/edit tasks with image upload. Follow the existing glass/navy theme.
- Frontend PictureVisual: show image_url when present, otherwise the existing emoji/chart fallback.

## 6. Tests and verification
- Add pytest tests (backend/tests/test_db.py) using a temporary SQLite DB and FastAPI TestClient: register + login, wrong password ×5 → locked, ownership check (user B cannot read user A's patient), age 7 / 11 / 19 patients receive tasks from brackets 1 / 3 / 7, rotation returns an unattempted task, clinician-only admin endpoints.
- Run the full test suite and npm run typecheck, fix all failures, then start backend and frontend and confirm sign-up → assessment tasks shows the correct bracket with a picture.
- Update README.md (database section, seeding, adding images, migrations).
- Show me complete corrected files for anything you change, and summarise what changed at the end.