# SpeakFree – Component 3: Multi-Disorder Severity Classification & Risk Prediction
Student: I.L.S. Tharushan (IT21315114) · runs inside the integrated backend, after Component 2.

## ★ Novelty – severity classification via a trained model cascade

```
C1 acoustic windows ──► stage 1  TORGO RandomForest (REAL data)            → P(dysarthria)
                                                                                 │
C2 hand-off + C1 biomarkers ──► 17-feature vector (feature_adapter.py) ◄────────┘
                                   ├─► stage 2  RF disorder classifier   P(normal | stuttering | dysarthria | articulation)
                                   ├─► stage 2  RF severity estimator    P(level 1..4)
                                   └─► stage 2  multi-label RF           P(repetition), P(prolongation), P(block)
                                                         │
uncertainty.py  max-prob confidence · normalised entropy · RF tree disagreement · temperature hook
unified_score.py  ★ fusion:  E[level] = Σ l·P(l);  normal ⇒ level ≤ 2;  A_C2 ≤ 45 or P(dys) ≥ 0.8 ⇒ +1;
                  risk = f(level, confidence);  every rule that fires is written to scoring_explanation
report.py         public contract → Component 4 (therapy_focus, severity_level, disorder_breakdown, …)
```

### Why a cascade
TORGO is the only real corpus available and it is labelled healthy/dysarthria only. The real
stage-1 model is trained on it (speaker-independent 5-fold GroupKFold). Its output becomes a feature
of the stage-2 models, which need labels no available corpus provides (4-way disorder, level 1–4,
stuttering events).

### Acoustic windows (`component3/acoustic_windows.py`)
Raw audio is never stored, so Component 1 calls this while the recording is in memory: up to three
3-s windows per recording, each starting 0.4 s before a speech interval (TORGO-like clips), with a
line-for-line port of the TORGO feature extractor (RMS, ZCR, spectral, pYIN F0, 13 MFCC).

### Feature vector (`component3/common.py`, 17 features)
C2 articulation score, clear-word ratio, kept-token confidence · C1 ASR confidence, dysfluency ratio,
fluency, pronunciation, wpm, articulation rate, pause rate, longest pause · C2 filler / repetition /
prolongation rates, long pauses per min · C1 flagged sounds · stage-1 P(dysarthria). Missing values
are imputed with documented defaults and reported (`imputed` in the admin dashboard).

## Models (`models/`) and training (`training/`)

```powershell
# from speakfree-component3\backend, with the platform venv
..\..\speakfree-component1\backend\venv\Scripts\python training\train_all.py   # ~1 min, writes models\ + model_card.json
..\..\speakfree-component1\backend\venv\Scripts\python training\evaluate.py
```

| Model | Data | Validation | Result (held-out) |
|---|---|---|---|
| `dysarthria_real_torgo.joblib` | **TORGO, real** – 16 552 utterances, 15 speakers | 5-fold GroupKFold by speaker | balanced acc 0.71 · ROC-AUC 0.77 |
| `disorder_classifier.joblib` | SYNTHETIC_DEMO (3 600 rows) | stratified 75/25 | acc ≈ 0.90 |
| `severity_estimator.joblib` | SYNTHETIC_DEMO | stratified 75/25 | acc ≈ 0.84 · within ±1 level ≈ 1.0 |
| `stuttering_multilabel.joblib` | SYNTHETIC_DEMO | 75/25 | macro F1 ≈ 0.82 |

The synthetic set's `dysarthria_probability` column is **sampled from the real stage-1 model's
out-of-fold predictions** (`training/data/torgo/oof_probabilities.csv`), per TORGO speaker and by
TORGO severity group, so stage 2 learns how the real acoustic model behaves on unseen speakers.
Everything else in that set is synthetic: **not clinically validated, not a research accuracy claim.**

The models were saved with scikit-learn 1.9.1 (pinned in the platform requirements). If a model
file is missing or fails to load, a clearly-flagged rule-based fallback answers
(`model_status` in the report and a banner in the admin dashboard).

## End-to-end check on real speech (TORGO recordings sent through the full platform)
Severe dysarthric speaker M02 → dysarthria, Level 4, risk High. Mild dysarthric M03 / F04 →
dysarthria, Level 2. Control speakers → borderline at low confidence (flagged for professional
review). Mic and reading-task domain shift is the main limitation.

## Tests
```powershell
..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q    # from speakfree-component3\backend
```
