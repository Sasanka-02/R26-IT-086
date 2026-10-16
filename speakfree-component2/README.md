# SpeakFree Component 2: Articulation Score

Pipeline: **Component 1 → Component 2 → Component 3.** Component 2 receives Component 1's
`POST /api/v1/analyze` response (`AnalyzeResponse`, schema 1.0.0), calculates a 0–100
**articulation score**, and POSTs the result to Component 3 (Multi-Disorder Severity
Classification). The formulas follow the *Component 2 Formula Alignment* document; code is in
[articulation_score.py](backend/services/articulation_score.py).

## Fields read from Component 1
| Component 2 term | Component 1 field |
|---|---|
| reference text (Method A) | `reference_text`, used only when `task_type = "reading"` |
| words | `word_segments[].word` |
| token probabilities P(t) | `word_segments[].tokens[].probability` (Equation 1) |
| low-confidence word | `word_segments[].is_dysfluency_candidate` (C_word < `dysfluency_threshold`, Equation 2) |
| confidence fallback | `overall_confidence_percent` ÷ 100 (Equation 3, includes fillers) |
| SNR | `acoustic_features.snr_db` |
| passed through to Component 3 | `analysis_id`, `session_id`, `patient_id`, `age_bracket`, `task_type` |

Shared rules: **R1**: the threshold is read from `dysfluency_threshold` (currently 0.60), never
redefined. **R2**: words are lower-cased, and only letters and apostrophes are kept. **R3**:
confidence uses Component 1's own equations; Component 2 does not re-run speech recognition.

## How the articulation score is calculated

**Step 1, filler removal.** A segment whose normalised word is in
F = {um, uh, er, erm, hmm, hm, ah, mm} is removed. The remaining words form the kept list W.
The number removed is sent as `filler_count`, a fluency signal that is not part of the score.

**Step 2, method selection.** Method A is used if `task_type == "reading"` and `reference_text`
is not null. Otherwise Method B is used.

### Method A: word accuracy (reading task)
```
WA = 100 × max(0, 1 − (S + D + I) / N)
```
N = words in `reference_text`. S, D and I come from a word-level Levenshtein alignment of
`reference_text` against W. These are recomputed after filler removal, so Component 1's
`wer.*` and `word_accuracy_percent` are not reused (they count each filler as an insertion).
Basis: Maier et al. (2009), Speech Communication 51(5):425–437.

### Method B: confidence and clear-word ratio (picture, scenario)
```
C   = (1/M) × Σ P(tⱼ)                over the M tokens of the kept words W
CWR = (N − L) / N                    N = |W|, L = kept words with is_dysfluency_candidate
Articulation = 100 × (0.5 × C + 0.5 × CWR)
```
If tokens are missing, C = `overall_confidence_percent` / 100 and the flag
`confidence_includes_fillers` is set. If there is no confidence at all, the score is 100 × CWR
and the flag `confidence_missing` is set.

### Worked examples (in [backend/samples](backend/samples))
- **Picture task** ([component1_output_example.json](backend/samples/component1_output_example.json)):
  "the boy is um the boy is climbing on the tree". N = 10, M = 11, C = 9.35 / 11 = 0.85, L = 1
  ("climbing", C_word 0.50), CWR = 0.90, so the score is 100 × (0.5 × 0.85 + 0.5 × 0.90) =
  **87.5 (good)**.
- **Reading task** ([component1_reading_example.json](backend/samples/component1_reading_example.json)):
  the reference is "The cat sat down. I see a red kite." (N = 9) and the kept words are "the cat
  sat sat down i see a wed kite". S = 1, D = 0, I = 1, so WA = 100 × (1 − 2/9) = **77.78 (fair)**.
  Component 1's own `word_accuracy_percent` is 66.67, because it also counts "um".

### Level and reliability
- `articulation_level`: good ≥ 85, fair 65–<85, poor 50–<65, very_poor < 50 (cut-offs borrowed
  from the PCC severity bands).
- `reliability_flags`: `too_few_words` (N < 10), `noisy_recording` (`snr_db` < 15),
  `confidence_missing`, `confidence_includes_fillers`, `schema_mismatch` (schema major version
  ≠ 1). `reliability` is `reduced` if any flag is set, otherwise `normal`. Flags never change
  the score.

## Sending to Component 3
Set Component 3's endpoint before starting the backend:
```powershell
$env:SPEAKFREE_COMPONENT3_URL = "http://<component3-host>:<port>/<path>"
```
Component 2 POSTs this payload as JSON:
```json
{
  "schema_version": "3.1",
  "source_component": "Component 2 - Alignment and Articulation Analytics",
  "analysis_id": "an-0001",
  "session_id": "demo-session-001",
  "patient_id": "P-001",
  "age_bracket": 1,
  "task_type": "picture",
  "articulation_score": 87.5,
  "articulation_level": "good",
  "method": "B_confidence_clear_word_ratio",
  "formula": "Articulation = 100 x (0.5 x C + 0.5 x CWR),  CWR = (N - L) / N",
  "formula_inputs": {"N_kept_words": 10, "M_kept_tokens": 11, "C_confidence": 0.85,
                     "C_source": "eq3_kept_tokens", "L_dysfluency_candidates": 1,
                     "CWR_clear_word_ratio": 0.9, "dysfluency_threshold": 0.6},
  "filler_count": 1,
  "reliability": "normal",
  "reliability_flags": [],
  "generated_at": "2026-10-16T18:04:32+00:00"
}
```
`method` is `A_word_accuracy`, `B_confidence_clear_word_ratio` or `pcc_r` (see below). The API
response always includes `component3_delivery.status`: `sent`, `failed` (with the error),
`not_configured` or `not_sent` (no score). A failed delivery does not fail the request.

## Endpoints
| Endpoint | Input | Output |
|---|---|---|
| `POST /api/v1/component2/from-component1` | **Component 1 JSON as the request body** (also accepts `{"component1_output": {...}}`) | **main pipeline**: score, sent to Component 3 |
| `POST /api/v1/component2/from-component1-audio` | multipart: `component1_json` (string), `file` (session recording), optional `target_text` | phoneme-level PCC-R, sent to Component 3 |
| `POST /api/v1/component2/analyze` | multipart: `file`, optional `target_text` | PCC analysis of a recording alone (not sent) |

Component 1 can call the main endpoint directly:
```powershell
curl.exe -X POST http://localhost:8000/api/v1/component2/from-component1 `
  -H "Content-Type: application/json" --data-binary "@backend/samples/component1_output_example.json"
```

## Optional: PCC-R when the recording is available
If the session recording is sent too (`from-component1-audio`), Component 2 runs a phoneme
recogniser (`facebook/wav2vec2-lv-60-espeak-cv-ft`) and scores each target consonant. The score
sent to Component 3 is then:
```
PCC-R = (correct + distorted target consonants) / target consonants × 100
```
(Shriberg et al., 1997, *J Speech Lang Hear Res* 40(4):708–722, DOI 10.1044/jslhr.4004.708).
The JSON-only score is still reported alongside it. Code:
[pcc_scoring.py](backend/services/pcc_scoring.py). To check the PCC against a therapist's
consonant-by-consonant scoring, use `python -m validation.validate_pcc`.

## Run backend
```powershell
cd backend
# first time only:
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
# every time:
$env:SPEAKFREE_COMPONENT3_URL = "http://<component3-host>:<port>/<path>"
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```
The JSON-only pipeline needs no ML models. The optional audio path needs FFmpeg, and on first
use it downloads the phoneme model (about 1.2 GB).

## Run frontend
```powershell
cd frontend
npm install   # first time only
npm run dev
```
Load a Component 1 JSON file and click **Calculate and send to Component 3**.

## Tests
```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

## Limitations
- Method B measures how well an ASR recognised the words, as a proxy for articulation. ASR
  confidence also falls with noise, accent and unusual vocabulary, so the score should be
  validated against therapist intelligibility ratings before any clinical use.
- Method B cannot detect a mispronounced word that the ASR still recognises correctly. Use
  tasks with a target text (Method A), or send the recording (PCC-R), for a stricter score.
- Component 1's low-confidence threshold is defined by Component 1, so L depends on it.
