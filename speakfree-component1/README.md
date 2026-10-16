# SpeakFree – Component 1
**Noise-Robust Speech Screening & Feature Extraction** · Research Project R26-IT-086 (SLIIT)

Novelty: **ASR confidence from Whisper token log-probabilities used as an objective clinical biomarker**
for dysfluency, hesitation and distortion.

```
Eq.1  P(t_i)      = exp(logprob_i)
Eq.2  C_word      = (1/k) Σ exp(logprob_i)            → word flagged if C_word < 0.60
Eq.3  C_overall   = ((1/N) Σ exp(logprob_i)) × 100
```

---

## 1. Folder structure

```
speakfree-component1/
├── README.md
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── alembic.ini             # Alembic config (URL comes from DATABASE_URL)
│   ├── migrations/             # Alembic env.py + versions/0001_initial_schema.py
│   ├── config.py               # all settings (.env overrides)
│   ├── database.py             # SQLAlchemy models: User, Patient, AssessmentTask, TaskAttempt, Analysis, ScreeningSession
│   ├── age_brackets.py         # DOB → age → bracket (6–20)
│   ├── auth.py                 # bcrypt + JWT + login verification (lockout)
│   ├── schemas.py              # Pydantic models + inter-component JSON contract
│   ├── task_service.py         # age-based task delivery + rotation (least-attempted first)
│   ├── task_bank.py            # SEED DATA ONLY: 84 tasks (7 brackets × reading, 3 picture, 3 scenario, 5 questions)
│   ├── seed.py                 # idempotent: task_bank.py → assessment_tasks table
│   ├── static/tasks/           # task images <task_id>.png|jpg|webp, served at /static/tasks
│   ├── audio_preprocessing.py  # FFmpeg decode, noise reduction, VAD, pause-preserving trim
│   ├── asr_service.py          # Whisper + log-prob confidence (Eq. 1–3)  ← NOVELTY
│   ├── feature_extraction.py   # Librosa: WPM, articulation rate, energy, RMSE, ZCR, SNR, pitch
│   ├── scoring.py              # explainable scores, WER, findings, screening indicator
│   ├── session_summary.py      # pools all recordings of a session → session-level C1 output
│   ├── streaming.py            # WebSocket contract for Component 4
│   ├── main.py                 # FastAPI routes
│   ├── tests/test_core.py      # unit tests for equations, VAD, scoring, session pooling, seed data
│   ├── tests/test_db.py        # API + DB tests: login lockout, ownership, age delivery, rotation, admin
│   └── tools/ws_test_client.py # WebSocket latency test
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── vite-env.d.ts
        ├── types.ts
        ├── api/client.ts
        ├── context/AuthContext.tsx
        ├── context/AssessmentContext.tsx  # current session: recordings + task-set snapshot
        ├── utils/age.ts
        ├── utils/recordingStore.ts        # IndexedDB: unfinished sessions survive a page reload
        ├── components/
        │   ├── ui.tsx                     # theme helpers: logo, score ring, gauge, scene illustrations
        │   ├── AppLayout.tsx              # header + sidebar shell
        │   ├── Recorder.tsx               # MediaRecorder capture + level meter
        │   ├── AuthFlow.tsx               # login, sign-up, role, DOB→age, consent
        │   └── AsrConfidenceDashboard.tsx # per-recording: waveform timeline, heat-map transcript
        └── pages/
            ├── assessment/
            │   ├── AssessmentOverview.tsx # 3 task cards + progress + "Analyse Now"
            │   ├── TaskPages.tsx          # 1 Picture · 2 Scenario · 3 Pre-defined Questions
            │   └── AnalysePage.tsx        # uploads each recording, then finalizes the session
            ├── SessionDashboard.tsx       # session-level ASR confidence + Component 1 output
            ├── TaskLibrary.tsx            # clinician-only: manage tasks + pictures per age bracket
            ├── DashboardHome.tsx
            └── ProgressPage.tsx
```

---

## 2. Prerequisites (Windows)

| Tool | Install |
|---|---|
| Python 3.11 | python.org (tick "Add to PATH") |
| Node.js 20 LTS+ | nodejs.org |
| FFmpeg | `winget install Gyan.FFmpeg` then **restart VS Code** and check `ffmpeg -version` |

---

## 3. Backend setup (PowerShell, inside `backend/`)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -r requirements.txt       # first time takes a while (torch + whisper)
copy .env.example .env                # then edit JWT_SECRET
python -m pytest -q                   # 27 tests should pass
alembic upgrade head                  # create / update the database schema
python seed.py                        # load the task library (safe to run again)
uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3
```
(`--timeout-graceful-shutdown` stops `--reload` from hanging on open browser connections. Once the Whisper
model has been loaded, `--reload` can still hang on Windows – stop the server with Ctrl+C and start it again.)

* API docs: http://localhost:8000/docs
* First analysis downloads the Whisper model (~140 MB for `base.en`) to `%USERPROFILE%\.cache\whisper`.
  Call `POST /api/v1/system/warmup` once to pre-load it.
* Slow PC? Set `WHISPER_MODEL=tiny.en` in `.env`. NVIDIA GPU? Install CUDA torch and it is used automatically.

## 4. Frontend setup (second terminal, inside `frontend/`)

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```
Open http://localhost:5173 → **Create an account** → choose a role → enter DOB → consent → Assessment Tasks.

**Screening flow**
1. Record the three tasks: **Picture Description**, **Scenario Description** and **Pre-defined Questions**
   (three questions, one recording each). Recordings stay in the browser and can be replayed or re-recorded.
2. When everything is recorded, press **Analyse Now**. Each recording is sent to `POST /api/v1/analyze`
   (progress shown per recording), then `POST /api/v1/sessions/{id}/finalize` pools them.
3. The **Screening Results** dashboard shows the pooled ASR confidence (Eq. 3 over every token of the session),
   word-weighted scores, screening level, per-task results, word-confidence distribution, sound findings,
   acoustic summary and the JSON hand-off for Components 2 & 3. Each task links to its word-level dashboard.

Clinicians also get a **Task Library** page in the sidebar to add, edit, activate/deactivate tasks and upload pictures.
(Microphone recording works on `localhost` or HTTPS only.)

### Database, migrations and the task library

* **Engine:** SQLite for development (`DATABASE_URL=sqlite:///./speakfree_c1.db`). Every column type is portable;
  for PostgreSQL run `pip install "psycopg[binary]"` and set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/speakfree`.
  SQLite runs with `PRAGMA foreign_keys=ON` so foreign keys are enforced like on PostgreSQL.
* **Tables:** `users` (+ `failed_logins`, `locked_until`, `last_login_at`), `patients`, `assessment_tasks`,
  `task_attempts`, `analyses` (`task_id` → `assessment_tasks.id`), `screening_sessions`.
* **Migrations (Alembic):** `alembic upgrade head` applies them; the API also does this at startup while
  `AUTO_MIGRATE=true`. After changing a model in `database.py`:
  ```powershell
  alembic revision --autogenerate -m "describe the change"   # then review the file in migrations/versions/
  alembic upgrade head
  ```
* **Databases created before Alembic** (no `alembic_version` table) cannot be upgraded. Stop the backend, delete
  `backend/speakfree_c1.db`, set a new `JWT_SECRET` in `.env` (old browser tokens would otherwise point at new
  user ids), then run `alembic upgrade head` and `python seed.py`. Accounts and results in the old file are lost.
* **Seeding:** `python seed.py` copies `task_bank.py` into `assessment_tasks` and skips ids that already exist, so
  clinician edits are never overwritten. Each bracket has 1 reading, 3 picture, 3 scenario and 5 question tasks.
* **Task delivery:** `GET /api/v1/tasks` computes the age from the date of birth (today), maps it to a bracket and
  picks one active task per type (three questions), preferring tasks the patient has attempted least
  (`task_attempts`, one row per analysed recording). Ties are broken randomly but stay stable until the patient's
  next attempt, so reloading the page mid-session never changes the tasks.
* **Images:** put `<task_id>.png|.jpg|.jpeg|.webp` in `backend/static/tasks/` and run `python seed.py` again, or
  upload one in the clinician **Task Library** page (max 5 MB, signature-checked). Without an image the emoji /
  chart illustration (`visual_json`) is shown. See `backend/static/tasks/README.md`.
* **Roles & views:** patients, guardians and clinicians see the simple, plain-language results page
  (`/sessions/{id}`) with next steps and a printable clinical report (`/sessions/{id}/report`). The built-in **admin**
  sees the patient directory (`/admin/patients`), each patient's profile and history, and the full technical session
  dashboard with every equation. Admin credentials are hardcoded in `config.py` (`admin_email` / `admin_password`,
  default `admin@speakfree.lk` / `SpeakFree@Admin2026`); the account is created at startup. **Change them before any
  real deployment.** Raw audio is still never stored, so the admin history shows "audio not retained".
* **Login verification:** an unknown email and a wrong password get the same 401. After `MAX_FAILED_LOGINS` (5) wrong
  passwords the account is locked for `LOCKOUT_MINUTES` (15) and login returns **423** "Account locked, try again in
  N minutes". A successful login resets the counter and records `last_login_at`.

---

## 5. API summary

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | role, DOB / child DOB, consent → JWT |
| POST | `/api/v1/auth/login` | email + password → JWT (401 generic, 423 while locked) |
| GET | `/api/v1/auth/me` | current user + patients |
| GET/POST | `/api/v1/patients` | list / add patients (guardian, clinician) |
| GET | `/api/v1/tasks?patient_id=` | age-bracket tasks from the DB: reading, picture, scenario, 3 questions (+ `image_url`) |
| **POST** | **`/api/v1/analyze`** | multipart: `audio`, `session_id`, `patient_id`, `age_bracket`, `task_type` (picture · scenario · questions · reading), `task_id` |
| GET | `/api/v1/results/{analysis_id}` | full result |
| GET | `/api/v1/sessions/{session_id}/results` | all results in a session (for C2 / C3) |
| POST | `/api/v1/sessions/{session_id}/finalize` | body `{patient_id}` → pool all recordings into the session-level C1 output |
| GET | `/api/v1/sessions/{session_id}/summary` | stored session-level C1 output |
| GET | `/api/v1/patients/{id}/sessions` | list of finalized screenings |
| GET | `/api/v1/patients/{id}/history` | per-recording score history |
| GET | `/api/v1/admin/tasks?age_bracket=&task_type=&include_inactive=` | clinician: list tasks + attempt counts |
| POST | `/api/v1/admin/tasks` | clinician: multipart task fields + optional `image` (jpg/png/webp ≤ 5 MB) |
| PATCH | `/api/v1/admin/tasks/{id}` | clinician: edit, `is_active`, replace `image` or `remove_image` |
| GET | `/api/v1/admin/patients` | **admin**: patient directory (last session, total sessions, latest risk) |
| GET | `/api/v1/admin/patients/{id}` | **admin**: patient profile + session history with recordings |
| GET | `/api/v1/admin/patients/{id}/sessions` | **admin**: session history only |
| GET | `/static/tasks/{file}` | task images |
| WS | `/ws/therapy/{session_id}?token=` | Component 4 live audio (PCM16, ≤ 300 ms chunks) |
| WS | `/ws/therapy/{session_id}/listen?token=` | Component 4 consumer |

### Key fields of the `/api/v1/analyze` response (contract for Components 2 & 3)
```json
{
  "schema_version": "1.1.0",
  "analysis_id": "…", "session_id": "…", "patient_id": "SF-1A2B3C4D",
  "task_type": "reading", "age_bracket": 3,
  "transcript": "Every Saturday Nimal helps …",
  "overall_confidence_percent": 87.4,
  "asr_accuracy_percent": 93.6,
  "fluency_score": 81.2,
  "pronunciation_score": 88.9,
  "articulation_score": 84.0,
  "overall_speech_score": 86.1,
  "dysfluency_threshold": 0.6,
  "word_segments": [
    { "index": 0, "word": "Every", "start": 0.52, "end": 0.86, "confidence": 0.9731,
      "is_dysfluency_candidate": false, "level": "high",
      "tokens": [{ "token": " Every", "token_id": 6109, "logprob": -0.0273, "probability": 0.9731 }] }
  ],
  "low_confidence_regions": [], "pauses": [], "phoneme_findings": [],
  "acoustic_features": { "words_per_minute": 128.4, "articulation_rate_syll_per_sec": 4.1,
    "energy_mean_db": -24.3, "rmse_mean": 0.061, "zcr_mean": 0.087, "snr_db": 27.5, "…": "…" },
  "screening_indicator": { "severity_hint": 1, "label": "Typical range", "risk": "low" }
}
```

---

## 6. Design notes for the viva
* **Teacher-forced log-probs:** after Whisper transcribes, the decoder is re-run on each word's exact BPE tokens,
  so every token gets `log P(token | audio, previous tokens)`. Those feed Eq. 1–3 directly.
* **Verbatim prompt:** Whisper normally deletes fillers; a verbatim initial prompt keeps "um/uh/repetitions",
  which are exactly the events we want to score.
* **Pause preservation:** only leading/trailing silence is trimmed. Internal gaps < 250 ms are merged as normal
  co-articulation; gaps ≥ 250 ms are kept and reported as clinically significant pauses.
* **Privacy:** audio is written to a temp file for decoding and deleted straight after analysis. Playback in the
  dashboard uses the blob still in the user's browser.
* **No training:** all models are pre-trained (Whisper, optional HuBERT). Scores are transparent formulas
  (see `scoring.py`) so they can be validated against clinician judgement.
* **Hallucination guard:** Whisper can "transcribe" tones/noise or loop ("T-T-T…" ×100) with high confidence.
  `asr_service.segment_rejection_reason` drops a segment before Eq. 1–3 when `no_speech_prob ≥ 0.75`, or when
  `compression_ratio > 2.4` **and** > 8 words/s (an impossible rate – slow genuine stutter repetitions are kept).
  If nothing valid remains the API returns 422 asking for a re-recording. Tune via `NO_SPEECH_THRESHOLD`, `MAX_WORDS_PER_SEC`.
* **Unfinished sessions** are kept in the browser's IndexedDB so a page reload does not lose recordings; they are
  deleted from the browser as soon as the session has been analysed.
* Age-norm ranges in `scoring.py` are approximate and should be calibrated with the clinical supervisor.

---

## 7. Integration with Components 2–4 (this backend is the host app)

See the project root `README.md` for the full picture. In short:

* **Schema 1.2.0** of `/api/v1/analyze` adds `model_features.acoustic_biomarker_windows`: numeric
  TORGO-style features (no audio) computed while the recording is in memory, for Component 3.
  `ENABLE_ACOUSTIC_BIOMARKERS=false` turns it off.
* **`POST /api/v1/sessions/{id}/finalize`** now also runs `integration/pipeline.py`:
  C2 articulation report → C3 severity report → C4 therapy profile, stored in `pipeline_runs` and
  `therapy_profiles` (migration `0002`). A failure there never fails the patient's screening.
  `RUN_PIPELINE_ON_FINALIZE=false` turns it off.
* New endpoints (`integration/routes.py`):

| Method | Path | Who |
|---|---|---|
| GET | `/api/v1/admin/pipeline` | admin – every run + KPIs |
| GET / POST | `/api/v1/admin/pipeline/{session_id}` · `/rerun` | admin – C1/C2/C3/C4 detail, re-run |
| GET | `/api/v1/admin/models` | admin – C2 equations, C3 model card, C4 engine settings |
| GET | `/api/v1/admin/patients/{id}/therapy` | admin – therapy monitor |
| GET | `/api/v1/therapy/{patient_id}/plan` | owner – patient-safe adaptive plan |
| POST | `/api/v1/therapy/{patient_id}/attempts` | owner – save an exercise result |
| GET / POST | `/api/v1/therapy/{patient_id}/assistant` · `/chat` | owner – AI assistant |
| WS | `/ws/therapy-live/{live_id}?token=` | live coaching (metrics only) |
