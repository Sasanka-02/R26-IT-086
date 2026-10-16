# SpeakFree – Component 2: Articulation Score

Runs inside the integrated backend (`speakfree-component1/backend/integration/pipeline.py`) right
after Component 1 finalises a screening session. Input: the C1 session summary + every
per-recording C1 `AnalyzeResponse`. Output: the C2 report (admin dashboard **C2 · Articulation**)
whose `component3_input` block is the hand-off to Component 3.

## ★ Novelty – the articulation score (`component2/articulation_score.py`)

Every input comes from Component 1's own fields: same dysfluency threshold (R1), same word
normalisation (R2), same confidence equations (R3). Component 2 never re-runs ASR.

```
Step 1  W = word_segments without fillers F = {um, uh, er, erm, hmm, hm, ah, mm}

Method A – reading task with reference text
  C2-Eq.1  WA = 100 × max(0, 1 − (S + D + I) / N)          (word Levenshtein, after filler removal)

Method B – picture, scenario, questions
  C2-Eq.2  C   = (1/M) × Σ P(t_j)       over the M tokens of the kept words      (C1 Eq.1/3)
  C2-Eq.3  CWR = (N − L) / N            L = kept words with C_word < 0.60        (C1 Eq.2)
  C2-Eq.4  A   = 100 × (0.5 × C + 0.5 × CWR)

Session (component2/session_pipeline.py)
  C2-Eq.5  A_session = Σ_r N_r · A_r / Σ_r N_r              (word-weighted, so a 3-word answer
                                                              cannot outweigh a 90-word description)
```

Levels: good ≥ 85 · fair ≥ 65 · poor ≥ 50 · very poor. Reliability flags (`too_few_words`,
`noisy_recording`, `confidence_missing`, `confidence_includes_fillers`, `schema_mismatch`) never
change the score.

Worked examples (tests): picture sample → **87.5 (good)**; reading sample → **77.78 (fair)**.

## Fluency events (`component2/fluency_events.py`)

Counted from C1 word timings and pauses and passed to C3: fillers, word / phrase repetitions,
prolongations (word duration > max(0.9 s, 0.22 s × letters)), long pauses (≥ 1 s), plus rates.

## Hand-off to Component 3 (`component3_input`, schema 4.0)

`articulation_score`, `pooled_confidence_C`, `pooled_clear_word_ratio`, `fluency_events`, the C1
session biomarkers (`component1.*`), `flagged_sounds` and the TORGO `acoustic_biomarker_windows`
that C1 computed while the audio was in memory.

## Tests
```powershell
..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q    # from speakfree-component2\backend
```

The earlier stand-alone server, the PCC-R phoneme path (needs stored audio, which the platform
never keeps) and the separate frontend were removed; the originals are in the project backup.
