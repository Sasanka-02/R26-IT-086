# Component 1 – training & evaluation

Scripts here never run inside the app. Data stays outside the app's runtime paths; results are
written to `training/results/` so they can be reported in the thesis / viva.

## Noise-robustness evaluation (`eval_noise_robustness.py`)

Shows whether Component 1 still works when the recording is noisy – the "noise-robust" claim.

| | |
|---|---|
| Dataset | **TORGO** (Rudzicz, Namasivayam & Wolff, 2012) – dysarthric and control speakers reading prompts. Used for **evaluation only**; nothing is trained. Check the TORGO licence / terms of use before redistributing any audio. |
| Location | Not part of the app. The copy used here: `D:\SpeakFree_original_backup\speakfree-component3\speakfree-component2\backend\dataset\torgo` (`metadata.csv` + `audio/`). |
| Sample | Seeded (`--seed 42`), speaker-balanced: `--per-group` healthy + the same number of dysarthric utterances, sentences of ≥ 3 words. |
| Noise | `white`, `pink` (generated from the seed), `babble` (6 overlapping TORGO talkers who are not in the sample), or real noise recordings with `--noise-dir` (e.g. MUSAN / DEMAND `.wav`). |
| SNR | clean, 20, 10, 5, 0 dB (speech power / noise power). |
| Pipeline | The real C1 front end: `preprocess()` (noise reduction on **and** off, the configured VAD) → `WhisperConfidenceASR` (Eq. 1–3). |
| Metrics | WER vs the prompt · C_overall (Eq. 3) per group · **AUC** of (100 − C_overall) for dysarthric vs healthy with a bootstrap 95 % CI · speech detected · VAD frame F1 (Silero vs energy) against a consensus clean reference. |

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$TORGO = "D:\SpeakFree_original_backup\speakfree-component3\speakfree-component2\backend\dataset\torgo"
python training/eval_noise_robustness.py --torgo-dir $TORGO --vad-only              # VAD only, ~1 min
python training/eval_noise_robustness.py --torgo-dir $TORGO --quick                 # 8+8 utterances, babble, clean/10/0 dB
python training/eval_noise_robustness.py --torgo-dir $TORGO --per-group 20 --noise babble,white   # thesis run (hours on CPU)
```

Whisper on a laptop CPU takes several seconds per transcription and every utterance is run
(conditions × 2) times (noise reduction on / off), so the full run is best left overnight, or on a
GPU (`WHISPER_DEVICE=cuda`). Each run writes `training/results/noise_robustness_<timestamp>/`:

- `summary.md` – tables ready for the thesis; `summary.json` – the same numbers + run configuration
- `per_utterance.csv`, `vad.csv` – raw results (one row per utterance × condition)
- `vad_f1_vs_snr.png`, `wer_vs_snr.png`, `confidence_vs_snr.png`, `auc_vs_snr.png`

### Reading the results honestly

- **VAD.** Silero keeps detecting speech in white / pink noise down to 0 dB where the energy VAD
  collapses. In **babble** at moderate SNR the energy VAD can score higher: babble *is* speech, so a
  speech detector also hears the background talkers. Report both.
- **Biomarker.** C_overall falls as noise rises for everyone; what matters clinically is whether the
  **AUC** (separation of dysarthric from healthy speech) holds up, and down to which SNR.
- TORGO is a small corpus of adult speakers; results are not a clinical validation, and child speech
  (the app's main users) is likely to behave differently.

## Voice activity detection (`VAD_BACKEND`)

`audio_preprocessing.py` supports `VAD_BACKEND=silero` (default; Silero VAD, MIT licence, bundled
model, CPU, `pip install silero-vad`) and `VAD_BACKEND=energy` (adaptive energy threshold). If Silero
is not installed or fails, the energy VAD is used automatically. Both feed the same
`merge_intervals()` step, so the ≥ 250 ms clinical pause rule is identical.
