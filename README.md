# SpeakFree – AI-Based Speech Disorder Screening & Therapy Assistant
Research Project R26-IT-086 (SLIIT) · integrated platform of four components

```
 patient records 3 tasks ──► C1 Speech screening ──► C2 Articulation ──► C3 Severity model ──► C4 Adaptive therapy
 (browser)                   Whisper log-prob          score (novelty)     cascade (novelty)      plans + AI assistant
                             confidence (novelty)                                                 (novelty)
        ▲                                                                                              │
        └──────────────────────── practice results · re-screening every 14 days ◄──────────────────────┘
```

One FastAPI backend and one React frontend (both in `speakfree-component1/`, the host app).
Components 2–4 are plain Python packages in their own folders, imported in-process – no extra
servers. When a patient presses **Analyse Now**, the backend runs C1 → C2 → C3 → C4 and stores
every stage. **Patients never see the C2/C3 analysis** – they see the friendly C1 results page
and then their adaptive therapy plan. The **admin** account sees every stage.

## Folder structure

```
SpeakFree/
├── README.md                     ← this file
├── speakfree-component1/         C1 · Noise-robust speech screening  (HOST APP: backend + frontend)
│   ├── backend/
│   │   ├── main.py, asr_service.py, …     Component 1 (unchanged novelty: Eq. 1–3)
│   │   ├── integration/                    ★ connects the components
│   │   │   ├── __init__.py                 puts speakfree-component{2,3,4}/backend on sys.path
│   │   │   ├── hooks.py                    TORGO acoustic windows while audio is in memory (for C3)
│   │   │   ├── pipeline.py                 C1 session → C2 → C3 → C4 profile (runs on finalize)
│   │   │   └── routes.py                   admin pipeline API + patient therapy API + live WS
│   │   ├── account_routes.py               account settings + appointment requests
│   │   ├── migrations/versions/0002_…py    pipeline_runs, therapy_profiles, therapy_attempts, assistant_messages
│   │   ├── migrations/versions/0003_…py    appointment_requests
│   │   └── tests/test_integration.py       end-to-end C1→C4 tests
│   └── frontend/src/
│       ├── pages/admin/pipeline/           ★ admin: Pipeline overview, C2 / C3 / C4 dashboards, Models
│       ├── pages/therapy/                  ★ patient: Therapy plan, exercise session, AI assistant, therapy report
│       ├── pages/{Reports,Resources,Appointments,Settings}Page.tsx
│       ├── components/charts.tsx           dashboard chart primitives (SVG)
│       └── types/integration.ts
├── speakfree-component2/backend/
│   ├── component2/                         C2 · Articulation score  ★ novelty: articulation_score.py
│   ├── samples/  tests/
├── speakfree-component3/backend/
│   ├── component3/                         C3 · Severity classification ★ novelty: model cascade + fusion
│   ├── models/                             trained RandomForest bundles + model_card.json
│   ├── training/                           train_all.py, TORGO features, synthetic-demo generator
│   └── tests/
└── speakfree-component4/backend/
    ├── component4/                         C4 · ★ novelty: adaptive plans (bandit.py, plan.py) +
    │                                            category-aware AI assistant (assistant.py)
    └── tests/
```

## The four novelties (search the code for `★`)

| Component | Novelty | Where |
|---|---|---|
| C1 | ASR-confidence biomarker – `P(t)=exp(logprob)`, `C_word`, `C_overall` | `speakfree-component1/backend/asr_service.py` |
| C2 | **Articulation score** – filler removal, `C = (1/M)ΣP(t)`, `CWR = (N−L)/N`, `A = 100(0.5C + 0.5CWR)`, reading `WA = 100·max(0,1−(S+D+I)/N)`, session pooling `A_session = ΣN_r·A_r / ΣN_r` | `speakfree-component2/backend/component2/articulation_score.py`, `session_pipeline.py` |
| C3 | **Severity classification via model** – stage 1 TORGO RandomForest on C1 acoustic windows → P(dysarthria); stage 2 RandomForest disorder classifier + severity estimator + multi-label stuttering model on a 17-feature vector from C1+C2; uncertainty; rule-guarded fusion with an explanation trail | `speakfree-component3/backend/component3/` (`unified_score.py`, `pipeline.py`, `dysarthria_acoustic.py`) |
| C4 | **Adaptive therapy plans + AI assistant per category** – C3 disorder → therapy focus (fluency / motor speech / speech sounds / maintenance); severity → dose + starting level; LinUCB contextual bandit with C3 context and a probability-weighted category prior; adaptive level ladder; measurable goals; re-screening loop; category-aware assistant (Naive-Bayes intents + optional Claude) | `speakfree-component4/backend/component4/` (`categories.py`, `bandit.py`, `plan.py`, `assistant.py`) |

## Run it on localhost – one click (Windows)

1. Install once: **Python 3.11**, **Node.js 20+** and **FFmpeg** (`winget install Gyan.FFmpeg`, then restart).
2. Double-click **`start-speakfree.bat`** in this folder.
   The first run creates the Python environment, installs all packages, migrates the database,
   loads the task library and runs the C2 → C3 → C4 pipeline for any older screenings. Then it opens
   two server windows (backend on port 8000, website on port 5173) and your browser at
   **http://localhost:5173**. Whisper and the Component 3 models load in the background.
3. Double-click **`stop-speakfree.bat`** to stop both servers.

| What | Where |
|---|---|
| Website | http://localhost:5173 |
| API documentation | http://localhost:8000/docs |
| Admin login | `admin@speakfree.lk` / `SpeakFree@Admin2026` |
| Database | `speakfree-component1/backend/speakfree_c1.db` (SQLite, migrations 0001–0003) |

Screenings made before the integration are processed with
`python tools/backfill_pipeline.py` (run automatically by the start script).

## Run it manually (Windows, PowerShell)

Prerequisites: Python 3.11, Node 20+, FFmpeg on PATH (see `speakfree-component1/README.md`).

```powershell
# backend (one venv for the whole platform)
cd speakfree-component1\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env            # set JWT_SECRET; optional ANTHROPIC_API_KEY for the AI assistant
alembic upgrade head              # applies 0001–0003 (also runs automatically at startup)
python seed.py
uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3

# frontend (second terminal)
cd speakfree-component1\frontend
npm install
npm run dev                       # http://localhost:5173
```

Call `POST /api/v1/system/warmup` once after starting: it loads Whisper and compiles the pYIN
pitch tracker used for the C3 acoustic windows (~20 s, once per process).

**Accounts.** Patients / guardians / clinicians register in the app. The built-in admin is
`admin@speakfree.lk` / `SpeakFree@Admin2026` (change it in `backend/config.py` before deployment).

## What each role sees

| Patient / guardian / clinician | Admin |
|---|---|
| Assessment Tasks → Analyse Now | **Patients** – directory, profile, history, therapy monitor |
| Friendly C1 results + clinical report | **Analysis Pipeline** – every session: C1 score, C2 articulation, C3 disorder/severity/risk, C4 focus |
| **Therapy Plan** – today's exercises, level ladder, week schedule, goals, progress, re-screen reminder | Session page with tabs **C1 · C2 · C3 · C4** (equations with real numbers, probabilities, feature vector, explanation trail) |
| **Exercise sessions** – reading/pacing, clear speech, loudness meter, breath support, sound drills, picture talk, DAF; live coaching | **Therapy monitor** – bandit ranking table (exploit/explore/prior), context vector, ladder history, attempts, assistant log |
| **AI Assistant** – coaching for their focus | **Models & Methods** – C2 equations, C3 model card + confusion matrices, C4 engine settings |
| **My Progress** – screening trend + therapy practice trend | **Appointments** – confirm (date-time + note) or decline requests |
| **Reports** – screening PDFs + therapy progress report PDF | **Task Library** – manage tasks and pictures per age bracket |
| **Resources** (guide for their plan first) · **Appointments** (request a session) · **Settings** (name, password, privacy) | **Settings** |

Patients never see a disorder name or severity level – only a friendly focus name such as
“Smooth, confident speech”.

## Tests

```powershell
cd speakfree-component1\backend; .\venv\Scripts\python -m pytest -q          # 33 tests (C1 + integration + account)
cd ..\..\speakfree-component2\backend; ..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q   # 16
cd ..\..\speakfree-component3\backend; ..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q   # 8
cd ..\..\speakfree-component4\backend; ..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q   # 11
cd ..\..\speakfree-component1\frontend; npm run typecheck
```

## Privacy

Raw audio is never stored: C1 deletes the temp file after analysis. Everything later components
need from the waveform (C3's TORGO acoustic windows) is computed during that analysis and stored
as numbers. Therapy exercises measure voicing, pauses and syllable rate in the browser and send
only those numbers.

## Limitations (read before reporting results)

* C3's stage-2 models are trained on a clearly-labelled **synthetic** dataset (its
  `dysarthria_probability` column is sampled from the real TORGO model's out-of-fold predictions).
  Only the stage-1 TORGO model reports real, speaker-independent metrics (balanced acc ≈ 0.71,
  ROC-AUC ≈ 0.77). Nothing here is clinically validated – it is a screening prototype.
* Browser microphones differ from TORGO's recording set-up; low-confidence results are flagged
  for professional review rather than over-claimed.
* C2's Method B measures how well the ASR recognised words, as a proxy for articulation.
