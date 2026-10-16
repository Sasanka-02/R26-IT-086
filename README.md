# SpeakFree

**AI-assisted speech screening and therapy for children and young people (ages 6–20)**
Research Project **R26-IT-086** · Sri Lanka Institute of Information Technology (SLIIT)

SpeakFree records short speaking tasks in the browser, analyses them with speech recognition and
acoustic features, estimates articulation quality and disorder severity, and turns the results into
an adaptive therapy plan. Raw audio is never stored on the server.

---

## Components

The project has four research components. Component 1 is the host application (FastAPI backend +
React frontend). Components 2–4 are Python packages that the host calls in sequence when a
screening session is finalized:

```
 Browser recording ──► C1 Screening ──► C2 Articulation ──► C3 Severity ──► C4 Therapy plan
                      (ASR confidence)   (0–100 score)       (classifier      (adaptive exercises
                                                              cascade)          + AI assistant)
```

| # | Component | Novelty | Location |
|---|---|---|---|
| 1 | **Noise-robust speech screening & feature extraction** | Whisper token log-probabilities used as an objective clinical biomarker for dysfluency, hesitation and distortion | [speakfree-component1/](speakfree-component1/) |
| 2 | **Articulation score** | 0–100 articulation score built from C1's word/token confidences (word accuracy on reading tasks, confidence-based on free speech) | [speakfree-component2/](speakfree-component2/) |
| 3 | **Multi-disorder severity classification** | Model cascade for stuttering / dysarthria severity with uncertainty and a unified score | [speakfree-component3/](speakfree-component3/) |
| 4 | **AI therapy assistant** | Adaptive weekly plans (LinUCB contextual bandit) and a category-aware assistant that answers from the patient's own results | [speakfree-component4/](speakfree-component4/) |

### Component 1 core equations

```
Eq.1  P(t_i)    = exp(logprob_i)
Eq.2  C_word    = (1/k) Σ exp(logprob_i)        → word flagged if C_word < 0.60
Eq.3  C_overall = ((1/N) Σ exp(logprob_i)) × 100
```

---

## Repository layout

```
SpeakFree/
├── README.md                    ← this file
├── speakfree-component1/        # host app – see its README for full details
│   ├── backend/                 # FastAPI, SQLAlchemy, Alembic, Whisper, Librosa
│   └── frontend/                # React + Vite + TypeScript + Tailwind
├── speakfree-component2/backend/component2/   # articulation score package
├── speakfree-component3/backend/component3/   # severity classification package
│   └── training/                               # training data (demo dataset) and scripts
└── speakfree-component4/backend/component4/   # adaptive plan + therapy assistant package
```

---

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite (PostgreSQL-ready), JWT + bcrypt |
| Speech / ML | OpenAI Whisper, PyTorch, Librosa, noise reduction + VAD, scikit-learn |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Tooling | pytest, FFmpeg |

---

## Quick start (Windows / PowerShell)

**Prerequisites:** Python 3.11, Node.js 20+, FFmpeg on `PATH` (`winget install Gyan.FFmpeg`).

**Backend** – one shared virtual environment runs the app and every component's tests:

```powershell
cd speakfree-component1\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env               # then set JWT_SECRET
python -m pytest -q
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3
```

API docs: <http://localhost:8000/docs>

**Frontend** (second terminal):

```powershell
cd speakfree-component1\frontend
npm install
copy .env.example .env
npm run dev
```

Open <http://localhost:5173>, create an account, and start the assessment tasks.
Microphone recording only works on `localhost` or HTTPS.

Full setup, database, API and design notes: [speakfree-component1/README.md](speakfree-component1/README.md).

---

## Roles

* **Patients, guardians, clinicians** – plain-language screening results, a printable clinical report,
  and progress history. Clinicians also manage the age-bracketed task library.
* **Admin** – patient directory, per-patient history, and the full technical dashboards
  (C1 equations, C2 articulation, C3 severity, C4 therapy monitor).

The default admin credentials are set in `speakfree-component1/backend/config.py`.
**Change them before any real deployment.**

---

## Privacy

* Uploaded audio is written to a temporary file for decoding and deleted right after analysis.
* Unfinished sessions are kept only in the user's own browser (IndexedDB) and removed once analysed.
* `.env` files, databases (`*.db`) and trained model weights are git-ignored and must never be committed.

---

## Project status

* **Component 1** – complete: screening flow, scoring, admin dashboards, tests.
* **Components 2–4** – integrated into the host as Python packages. Frontend panels for C2/C3/C4
  live in `frontend/src/pages/admin/pipeline/` and `frontend/src/pages/therapy/`.
* C3's saved scikit-learn models are tied to the installed scikit-learn version. If you upgrade it,
  retrain with `python training/train_all.py` from `speakfree-component3/backend/`.

---

## Team

Research project R26-IT-086, SLIIT.
