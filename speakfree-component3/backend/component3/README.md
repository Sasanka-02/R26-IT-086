# Component 3 — Multi-Disorder Severity Classification & Risk Prediction

**Student:** I.L.S. Tharushan — **IT21315114**
**Runs inside:** the existing Component 2 FastAPI backend (`speakfree-component2/backend`). No second server.

Component 3 **consumes Component 2 output** and never re-runs Component 1 / Component 2 processing.

```
Component 2 output
   -> feature_adapter.py     validate + impute + normalise -> internal feature vector
   -> classifier.py          4-class disorder  (RandomForest, predict_proba)
   -> stuttering.py          multi-label events: repetition / prolongation / block
   -> severity.py            Level 1-4  (RandomForest, predict_proba)
   -> uncertainty.py         max-prob confidence + entropy + RF tree disagreement + temperature hook
   -> unified_score.py       transparent "research prototype unified severity score" + risk
   -> report.py              structured clinical-screening JSON
```

## Module map

| File | Purpose |
|---|---|
| `common.py` | `FEATURE_ORDER` (the single feature contract), label spaces, model paths, `MODEL_VERSION` |
| `feature_adapter.py` | `adapt_features(component2_output)` — accepts the full C2 API response, the `component2_output` object, **or** just the `component3_ready_output` handoff dict; imputes missing MFA fields; preserves C2 confidence |
| `classifier.py` | `classify_disorder()` — trained RF; transparent heuristic fallback if model file missing (loudly flagged) |
| `stuttering.py` | `analyze_stuttering_events()` — `MultiOutputClassifier`; interface is model-agnostic for a later HuBERT swap |
| `severity.py` | `estimate_severity()` — RF over the 4 ordered levels + probability-weighted `expected_level` |
| `uncertainty.py` | `estimate_uncertainty()` + `apply_temperature()` |
| `unified_score.py` | `compute_unified_score()` — documented rules, returns a `scoring_explanation` trail |
| `report.py` | `build_report()` — the public output contract |
| `pipeline.py` | `run_component3(session_id, user_id, component2_output)` + `health()` |
| `schemas.py` | Pydantic request/response models |
| `_models.py` | lazy cached `joblib` loaders |

## API (registered on the Component 2 app under `/api/v1`)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/component3/health` | model-training status (`n/4`) |
| `GET` | `/api/v1/component3/model-card` | data sources, metrics, disclaimers |
| `POST` | `/api/v1/component3/analyze` | body: `{ session_id, user_id, component2_output, temperature? }` |

## Models

Run from the **backend** directory:

```bash
python Training/component3/train_all.py      # builds all 4 models + model_card.json
python Training/component3/evaluate.py       # prints stored metrics for each
```

| Model | Data | Validation | Notes |
|---|---|---|---|
| `disorder_classifier.joblib` | **SYNTHETIC_DEMO** | stratified 75/25 | 4-class — *not clinically validated* |
| `severity_estimator.joblib` | **SYNTHETIC_DEMO** | stratified 75/25 | Level 1-4 — *not clinically validated* |
| `stuttering_multilabel.joblib` | **SYNTHETIC_DEMO** | 75/25 | repetition/prolongation/block — *not clinically validated* |
| `dysarthria_real_torgo.joblib` | **TORGO (real research data)** | 5-fold GroupKFold by speaker (speaker-independent) | genuine result: balanced acc ≈ 0.73, ROC-AUC ≈ 0.77 |

If a model file is absent the pipeline still responds, using a clearly-labelled
heuristic fallback (`model_status` in the report shows this). It never returns
a hard-coded or faked "trained" result.

## Why a demo dataset?

TORGO — the only real dataset in the repo — is labelled `healthy` / `dysarthria`
**only**. It has no 4-way disorder labels, no Level 1-4 severity, and no
stuttering-event labels. The synthetic `component3_demo_dataset.csv` exists to
build and demonstrate the *full pipeline* with real scikit-learn training
(`fit` / `predict` / `predict_proba`, real train/test split, real metrics).
It is **not** a clinical or research-valid accuracy claim. The one real
research result is the TORGO speaker-independent dysarthria model.

## Tests

```bash
python tests/component3/test_pipeline.py          # no pytest needed
# or
python -m pytest tests/component3 -q
```
