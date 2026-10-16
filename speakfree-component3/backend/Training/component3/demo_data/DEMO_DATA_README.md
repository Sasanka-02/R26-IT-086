# SYNTHETIC DEMO DATA — NOT CLINICAL / NOT RESEARCH-VALID

`component3_demo_dataset.csv` is **generated** by
`Training/component3/make_demo_dataset.py` (fixed seed = 42).

Every row has `data_source = "SYNTHETIC_DEMO"`.

## Why it exists

The repository's only real dataset (TORGO, `dataset/torgo/`) is labelled
`healthy` / `dysarthria` only. Component 3 needs:

- 4-way disorder labels: `normal / stuttering / dysarthria / articulation`
- severity `severity_level` ∈ {1,2,3,4}
- stuttering-event multi-labels: `stutter_repetition`, `stutter_prolongation`, `stutter_block`

None of these exist in any real dataset in this repo. This synthetic file lets
the multi-disorder / severity / stuttering models be trained with a **real**
scikit-learn pipeline (real `fit` / `predict` / `predict_proba`, real
train/test split, real confusion matrices) so the Component 3 architecture is
demonstrably ML-driven — **not** hard-coded.

## What it is NOT

- NOT clinical data
- NOT a validated severity scale
- NOT a source of research-valid accuracy figures

The feature columns match `component3.common.FEATURE_ORDER` exactly — i.e. the
same fields the feature adapter produces from real Component 2 output — with
disorder-conditioned distributions documented in `make_demo_dataset.py`.

## Replacing it with real data (future work)

Swap in real labelled data with the same columns:
- SEP-28k → stuttering-event labels
- UA-Speech / TORGO severity ratings → `severity_level`
Then re-run `python Training/component3/train_all.py`.
