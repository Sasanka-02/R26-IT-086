# SpeakFree — Component 4: AI Therapy Assistant

Standalone project for R26-IT-086's Component 4 (privacy-preserving
real-time therapy module). Independent from Component 1 — its own
backend, frontend, ports, and fake auth/dashboard shell.

## What's implemented

- **SO1 — Real-time coach**: live pacing exercise with WebSocket feedback,
  computed only from on-device audio metrics (never raw audio).
- **SO2 — DAF module**: adaptive delay calibration protocol (5 trials,
  picks the delay minimising stutter events × rate deviation) plus the
  actual Web Audio delay-node exercise.
- **SO3 — Dashboard & adaptive plans**: a working (simplified) LinUCB
  contextual bandit selects next week's exercises from real reward
  signals; dashboard shows charted weekly trends.
- **SO4 — Federated learning**: presented as an architecture design
  (`federated_stub.py`), not a live training loop — accurately reflects
  that this requires real multi-device rollout, not fakeable in a demo.
- **SO5 — Differential privacy**: a real Laplace mechanism privatises
  stored dashboard statistics, and a real per-patient epsilon budget
  ledger is tracked and shown in the UI.
- **6th capability — biomarker comparison**: compares patient metrics
  (as Component 1 would produce them) against a normative profile,
  producing a delta vector and progress score.
- **Bonus — simple picture description**: an extra practice exercise
  (record → review → mark complete), reusing the same recorder pattern.

## Structure

```
speakfree-component4/
├── backend/
│   └── app/
│       ├── main.py            FastAPI entrypoint (therapy router only)
│       ├── core/config.py     settings
│       └── therapy/
│           ├── router.py          all /api/v1/therapy/* endpoints
│           ├── schemas.py         Pydantic models
│           ├── exercises.py       exercise bank (pacing/DAF/picture)
│           ├── session_store.py   in-memory live session state
│           ├── realtime_feedback.py  SO1 coaching logic
│           ├── bandit.py          SO3 LinUCB adaptive planner
│           ├── dashboard.py       SO3 trend data generator
│           ├── privacy.py         SO5 Laplace mechanism + budget ledger
│           ├── federated_stub.py  SO4 architecture design (not live)
│           └── biomarker.py       6th capability — normative comparison
└── frontend/
    └── src/
        ├── context/            AuthContext (fake), SessionContext
        ├── pages/               Landing, Login, Signup, Dashboard, Therapy
        ├── components/          shared recorder UI
        ├── hooks/useAudioRecorder.ts
        └── therapy/             all exercise + dashboard + privacy components
```

## Install & run

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```
No ffmpeg/Whisper/torch needed — Component 4 doesn't do ASR, so this
backend is much lighter than Component 1's.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Runs on **port 5174** (not 5173) so it can run alongside Component 1's
frontend without a port clash. Backend runs on **port 8001** for the
same reason — check `frontend/.env` points `VITE_API_BASE_URL` at
`http://localhost:8001`.

Add a picture-description stimulus image:
```
frontend/public/stimuli/images/picture-1.jpg
```

Visit `http://localhost:5174` → Get Started → (fake) signup → Dashboard
→ Open Therapy Assistant → all four tabs.

## Honest scope notes

- Auth/Dashboard shell is UI-only (localStorage), no real account backend.
- SO4 (federated learning) is documented architecture, not a live
  training loop.
- SO5's Laplace mechanism and privacy budget ledger are real, working
  differential privacy — not decorative.
