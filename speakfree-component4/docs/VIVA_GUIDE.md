# Component 4 — Viva Guide

**AI Therapy Assistant: personalised, adaptive and privacy-preserving speech-therapy practice.**

This guide explains every part of the component in plain language, where each
equation and constant comes from, how each part is validated, and how to run
the demo. Read sections 1–3 first; they cover what the panel asked for.

---

## 1. The one-minute explanation

Students who stutter practise at home: graded reading (Beginner → Intermediate →
Advanced/final stage), picture description, pacing and delayed auditory feedback.

1. **The browser measures, the server never hears.** While the student reads,
   the browser computes a few numbers twice a second (loudness, whether they are
   speaking, syllable peaks). Only those numbers are sent; audio never leaves
   the device.
2. **Each attempt gets an explainable score.** A linear model turns the numbers
   into a 0–100 practice-quality score and shows each factor's points.
3. **The score is validated against a therapist.** Therapists rate attempts 1–5.
   The app measures agreement (MAE, correlation), then *learns* the score's
   weights and thresholds from those ratings instead of guessing them.
4. **The system adapts.** Two strong readings unlock the next level; two difficult
   ones step back. A contextual bandit (LinUCB) picks the rest of each student's
   plan from their own results, and the reading speed adapts per student.
5. **The assistant explains and guides.** A trained intent classifier understands
   the student's question and answers from *their* data; an optional language
   model handles anything it is unsure about.
6. **The therapist stays in control.** They see every student, assign exercises,
   set the level, set measurable goals, write notes and rate attempts.
7. **Privacy is enforced.** Passwords are hashed, every endpoint checks the
   user's role, and statistics shared outside the clinic use differential privacy.

---

## 2. Panel comments and how they are addressed

| Panel comment | What was built | Where to show it |
|---|---|---|
| Output should be clear, not graphs | Plain-language cards, tables, level ladder, "What this means for you" | Student → *My Progress* |
| Output should change with different users | Every result is stored per account; plan, assistant, level, goals, badges all come from that user's data | Log in as two demo students |
| Assistant was missing | Intent classifier (87% cross-validated) + personal briefing + optional LLM | Student → *Assistant* |
| Adaptive learning was missing | Level engine, LinUCB plan with predicted score ± uncertainty, adaptive reading speed, therapist overrides | Student → *Weekly Plan*; Therapist → controls |
| Constants must not be guessed; derive from evidence | Ridge-regression calibration of every weight and threshold from therapist ratings | Therapist → *Model evidence* §2 |
| Validate output with an expert | Therapist 1–5 ratings, agreement metrics, leave-one-out validation, scatter plot | Therapist → *Model evidence* §1 |
| Need a clear understanding of the component | This guide, explanations built into every page | — |

---

## 3. Every equation, and where its numbers come from

### 3.1 Practice-quality score (`backend/app/therapy/scoring.py`)

```
score = clip( Σ wᵢ · xᵢ , 0, 100 )
```

| Factor xᵢ | Meaning | Starting weight |
|---|---|---|
| intercept | base score | 72 |
| live | 1 if live audio metrics exist (reading/pacing) | −32 |
| voicing | fraction of time the voice was active (0–1) | +85 |
| pauses_per_min | long pauses (≥ 3 s silence) per minute | −10 |
| quiet_per_min | "too quiet" warnings per minute | −4 |
| rate_deviation | \|measured wpm − target wpm\| / target wpm | −30 |
| rating | self-rating: easy +1, okay 0, hard −1 | +12 |
| short_attempt | 1 if the attempt lasted < 15 s | −15 |

**Why these starting values?** They encode the clinical intent: steady voicing
is good, long pauses and rushing are bad, a full-voicing reading with no pauses
scores ~100, a picture description with no live metrics starts at 72. They are
explicitly *starting values only* — the next step replaces them with evidence.

**Calibration from expert ratings (the answer to "don't guess constants").**
Therapists rate attempts 1–5, mapped to 0–100 as `(rating − 1) × 25`. With
`X` = factor values and `y` = therapist scores, the weights are re-estimated by
ridge regression shrunk towards the starting values:

```
w = (XᵀX + λI)⁻¹ (Xᵀy + λ·w_prior),   λ = 4
```

* With few ratings, `w` stays close to the starting values (stable).
* As ratings accumulate, the evidence dominates.
* Calibration switches on at 8 ratings (`MIN_RATINGS`), re-running every time
  a therapist saves a rating.

**Validation metrics** shown on the evidence page:
* MAE (mean absolute error) and RMSE between app score and therapist score
* Pearson correlation r
* % of attempts within ±15 points
* **Leave-one-out**: each rating is predicted by a model fitted *without* it,
  so the calibrated model's error is an honest estimate on unseen data.

**Thresholds.** "Strong" (counts towards levelling up) and "difficult" (counts
towards levelling down) are chosen as the cut-offs on the calibrated score that
best separate therapist-rated good (4–5) from not-good attempts, maximising
*balanced accuracy* = (sensitivity + specificity) / 2. Until each side has ≥ 3
rated attempts, the starting values 75 and 45 are used.

### 3.2 Speech rate (`frontend/src/therapy/useLiveFeedback.ts`, `exercises.py`)

* Browser: syllable nuclei are counted as peaks in the smoothed loudness
  envelope (sampled every 20 ms). A peak counts when energy rises above a floor
  and then drops by ≥ 35%, with peaks ≥ 120 ms apart (speech rarely exceeds
  ~8 syllables/second).
* Server: `words = syllables / syllables_per_word(passage)` where
  syllables-per-word is **measured from the passage text itself** (vowel-group
  counting), not a fixed constant. `wpm = words / minutes`.
* Limitation: an estimate from energy peaks, not speech recognition. It is
  accurate enough to say "too fast / on target / slower", which is how it is used.

### 3.3 Level engine (`adaptive.py`)

Replays the student's reading attempts in order:
* 2 strong in a row at the current level → move up
* 2 difficult in a row → move back down (never below Beginner)
* 2 strong at Advanced → final stage mastered

A therapist's level override restarts the replay from the chosen level.

**Adaptive reading speed:** each strong attempt at an exercise raises its
highlight speed by 10%, each difficult one lowers it by 10%, within 70–130% of
the passage's base speed.

### 3.4 LinUCB weekly plan (`bandit.py`)

Context vector for a student: `x = [1, level, recent average score, trend, comfort]`.
For each exercise (arm) the bandit keeps `A = I + Σ x xᵀ` and `b = Σ reward · x`:

```
θ          = A⁻¹ b
predicted  = θᵀ x
uncertainty = α · √(xᵀ A⁻¹ x),   α = 0.6
choose the exercise with the largest  predicted + uncertainty
```

* Untried exercises have large uncertainty, so the plan *explores*; exercises
  that worked get a high prediction, so it *exploits*.
* Reward = the attempt's score / 100.
* Each student's model is rebuilt by replaying their own history, so plans are
  fully personal and need no stored model.
* Order of the plan: therapist-assigned → current reading level → bandit picks
  (one per exercise type for variety).

**Why LinUCB rather than fixed rules or A/B testing?** It uses context (two
students at the same level can need different exercises), it learns online
from each session, and the uncertainty term guarantees exploration without
random guessing.

**Evidence (`simulation.py`, evidence page §3):** 60 simulated students with
known best exercises, 30 sessions each, fixed seed:

| Strategy | Average reward | Regret (lower is better) | Picks the best exercise (last 10) |
|---|---|---|---|
| LinUCB | ~79 | ~262 | ~39% |
| Random | ~70 | ~558 | ~10% |
| Fixed rotation | ~70 | ~558 | ~11% |

### 3.5 Assistant intent classifier (`intent_classifier.py`, `assistant.py`)

Multinomial Naive Bayes:

```
P(intent | words) ∝ P(intent) · Π P(word | intent)
P(word | intent)  = (count(word, intent) + α) / (total(intent) + α·|V|),   α = 0.2
```

Pre-processing: lower-case → synonym mapping ("fast/quick/slow" → *speed*,
"stammer/stuck/block" → *block*) → stop-word removal → light stemming.

* 18 intents, 156 labelled examples, **87% leave-one-out accuracy**.
* Confidence < 0.5 → not guessed: the optional language model answers (if
  `ANTHROPIC_API_KEY` is set, receiving only the student's practice summary),
  otherwise a safe "here's what I can help with" reply.
* Every reply shows its route and confidence, e.g. *Intent: progress · 94% confident*.

### 3.6 Differential privacy (`cohort_report.py`)

The treating therapist sees exact data. A **cohort report** meant for sharing
outside the clinic is released with the Laplace mechanism:

```
noisy value = true value + Laplace(0, sensitivity / ε)
```

* Privacy unit: one practice attempt. Count histograms have sensitivity 1
  (level histogram: 2, because one attempt can move a student between two
  levels); the mean score has sensitivity 100/n.
* Total ε is split across 4 statistic groups (sequential composition); each
  histogram costs its share once (parallel composition).
* Releases are cached per data snapshot, so repeating a request cannot average
  the noise away or drain the budget.
* The page shows the privacy/accuracy trade-off for ε = 0.25 … 5.

### 3.7 Usability evaluation (`survey.py`)

The System Usability Scale (SUS): 10 standard statements answered 1–5.

```
item score = answer − 1   (odd, positive statements)
           = 5 − answer   (even, negative statements)
SUS        = 2.5 × Σ item scores        (0–100; 68 = common average benchmark)
```

* Students are invited on the Practice tab after 3 exercises; therapists see an
  invitation at the top of the portal. One response per person.
* The evidence page (§6) reports the mean, standard deviation, 95% confidence
  interval (mean ± 1.96·SD/√n), student vs therapist scores, per-statement
  means and comments.
* **For the report:** ask 5–10 testers to use the app, then quote the mean SUS
  score, its confidence interval and how it compares with 68.

### 3.8 Security (`auth.py`)

* Passwords: PBKDF2-HMAC-SHA256, 200 000 iterations, random 16-byte salt.
* Tokens: `base64(payload).HMAC-SHA256(payload)`, 7-day expiry; tampering
  breaks the signature.
* Students can only access their own data (403 otherwise); therapist endpoints
  require the therapist role; therapist sign-up requires a clinic invite code.

---

## 4. Running the demo

```powershell
# backend (from backend/)
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m scripts.seed_demo        # demo accounts + data
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001

# frontend (from frontend/)
npm install
npm run dev     # http://localhost:5174

# tests (from backend/)
.\venv\Scripts\python.exe -m pytest -q
```

Demo logins (password `demo1234`): therapist `dr.silva@demo.local`; students
`amal@demo.local`, `nimali@demo.local`, `kasun@demo.local`, `ravi@demo.local`.
Therapist invite code for new therapist sign-ups: `SPEAKFREE-CLINIC`
(change with the `THERAPIST_INVITE_CODE` environment variable).
Remove demo data with `python -m scripts.seed_demo --clean`.

**Important:** the demo's expert ratings come from a *simulated* therapist so
the evidence page has content. For the final report, have a real speech
therapist rate real attempts on the student pages; the same page then shows
real validation results.

### Suggested 6-minute demo script

1. **Student (amal@demo.local)** — Practice tab: reading levels with locks;
   start a Beginner reading with the breathing warm-up; save the result and open
   *How this score was worked out*.
2. **Weekly Plan** — point at "Predicted score ≈ … (± …)" and *How the plan is
   chosen*.
3. **Assistant** — ask "Why did I get this score?", "Am I meeting my goals?",
   "I talk too fast". Show the intent/confidence tag.
4. **My Progress** — plain-language summary, goals, badges, first vs latest.
5. **Therapist (dr.silva@demo.local)** — alerts, student table; open Nimali:
   assign an exercise, add a goal, rate an attempt.
6. **Model evidence** — expert agreement before/after calibration, learned
   constants, LinUCB vs random, assistant accuracy, usability (SUS), DP trade-off.

---

## 5. Likely questions

**Is the score a clinical stuttering measure?** No — it is a practice-quality
score from on-device measurements. That is why it is validated against
therapist ratings and calibrated to them; the evidence page reports how well it
agrees.

**Where do your constants come from?** Starting values encode the clinical
intent and are documented; the deployed values are re-estimated from therapist
ratings by ridge regression, and the thresholds are chosen by balanced accuracy
against the same ratings. Leave-one-out validation shows the calibrated model
predicts unseen ratings better.

**Why ridge regression instead of plain least squares?** With few ratings,
plain least squares overfits and can flip signs. Shrinking towards the starting
weights keeps the model stable and only moves where the evidence is strong.

**What is ε?** The privacy-loss parameter: the smaller it is, the less any one
attempt can change what is released, and the more noise is added.

**Why is federated learning only a design?** It needs many real devices and a
training loop; the architecture is documented (`federated_stub.py`) and the
privacy pieces that can run on one machine (Laplace mechanism, budget) are live.

**What if the classifier misunderstands?** Below 50% confidence it does not
guess; it hands over to the language model or lists what it can help with.

**Limitations / future work:** speech rate is an energy-peak estimate, not ASR;
calibration quality depends on the number of real therapist ratings; the
simulation assumes stationary student benefit; storage is JSON files (move to a
database for production); add Sinhala/Tamil passages.
