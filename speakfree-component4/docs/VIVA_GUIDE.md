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
4. **The system adapts.** One strong reading unlocks the next level; two difficult
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
| Output should be clear, not graphs | A report card comes first: one sentence, a traffic light (Improving / Steady / Needs support), "This week", "Next step". Charts are behind a *Details* toggle. *Download report (PDF)* prints a clean report | Student → *My Progress*; Therapist → student page |
| Output should change with different users | Every result is stored per account. *Compare students* shows two students side by side: level, level timeline, plan, reading speeds, assistant answer | Therapist → *Compare students* |
| Assistant was missing | Intent classifier (87% cross-validated) + personal briefing + optional LLM | Student → *Assistant* |
| Adaptive learning was missing | Level engine with a visible **level timeline** ("Beginner → Intermediate on 3 Oct after 1 strong Beginner reading"), LinUCB plan with a **Why this plan for you?** box (the bandit's numbers in words), adaptive reading speed, therapist overrides | Student → *My Progress*, *Weekly Plan* |
| Constants must not be guessed; derive from evidence | Ridge-regression calibration of every weight and threshold from therapist ratings | Therapist → *Model evidence* §2 |
| Validate output with an expert | Therapist 1–5 ratings → MAE, Pearson r, % within 15, "strong vs expert 4–5" accuracy, Cohen's kappa between two raters. Clinician and synthetic ratings are reported **separately** | Therapist → *Model evidence* §1 |
| Validate the adaptive learning output | Therapist judges each generated weekly plan (appropriate / partly / not) → % agreement | Therapist → student page; *Model evidence* §4 |
| Need a clear understanding of the component | This guide, explanations built into every page | — |

### 2.1 Honest labelling of data

The demo seed script (`backend/scripts/seed_demo.py`) creates **synthetic data
for pipeline testing**: made-up students, attempts and ratings from a formula
(`_synthetic_rating`). Every such rating is stored with `source: "synthetic"`;
ratings and plan reviews made from any `@demo.local` account are also
synthetic. The scoring model fits on clinician ratings whenever any exist,
and the evidence page always shows the two sources apart. Say this
openly in the viva and the report: *"The seeded numbers test the pipeline;
the validation results are the clinician ones in §1."*

### 2.2 Real expert validation protocol (for the report)

1. **Recruit** one speech-language pathologist (hospital speech-therapy unit,
   university speech and hearing department, or private clinic) for a
   1–2 hour session. Create them a therapist account with the clinic invite
   code. Do **not** use a `@demo.local` account, or their ratings will be
   counted as synthetic.
2. **Volunteers** (8–10) each create a student account on the sign-up page
   (with consent).
3. **Validation session** (therapist menu → *Validation session*): pick the
   volunteer, add the second rater's name if there is one, pick an exercise.
   The volunteer does it on the laptop and saves. The SLP **listens to the
   recording on the same screen** and rates 1–5. The app's score stays hidden
   until the rating is submitted, so the rating is blind. Repeat for 30–50
   attempts across all exercise types. Recordings never leave the laptop;
   ratings are marked "rated while listening" and calibration re-runs on each.
4. **Second rater (optional):** type their name in *Rater 2*; both rate each
   attempt at the same sitting, and Cohen's kappa appears under *Agreement
   between two raters*.
5. **Plans:** on 10 student pages the SLP judges *Validate this week's plan*.
6. **Report** from *Model evidence*: §1 (MAE, Pearson r, % within ±15,
   strong-vs-4–5 accuracy, kappa) and §4 (% plans appropriate).
   *Rating sheet (CSV)* downloads every rating with rater and timestamp.
7. **Keep proof:** signed letter or email from the SLP, the CSV rating sheet,
   photos of the session.

### 2.3 Pilot study (for the report)

1. **Recruit** 5–10 users (not `@demo.local` accounts) and ask them to practise
   on most days for 1–2 weeks.
2. **Results fill in automatically** on *Model evidence* §7: each person's
   average score in their first week vs their last week, long pauses per
   reading, the mean change with a 95% confidence interval, how many improved,
   and an exact sign test (suitable for small groups). People join the
   analysis after 7+ days of practice with 2+ attempts in each week.
3. **Usability:** the SUS survey invites them after 3 exercises; §6 shows the
   mean SUS score and its confidence interval.
4. **Report** the §7 numbers, the SUS score, and attach *Pilot data (CSV)*.
   Be honest about the sample size: with 5–10 people this shows feasibility
   and a direction of change, not clinical efficacy.

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
* 1 strong attempt at the current level → move up
* 2 difficult in a row → move back down (never below Beginner)
* 1 strong at Advanced → final stage mastered

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
| LinUCB (live) | 79.4 | 262 | 39% |
| LinUCB + exercise features (candidate) | 79.5 | 256 | 52% |
| Random | 69.5 | 558 | 10% |
| Fixed rotation | 69.6 | 558 | 11% |

**Say the weakness first:** 39% best-exercise rate after 30 sessions means the
live engine is still learning. The learning curve is still rising, and regret is
already half that of a fixed plan.

**Exercise features (before/after):** the live model learns each exercise
separately, using only student features. `HybridLinUCB` adds exercise features
`[1, difficulty, difficulty², type one-hot]`, crossed with the student context,
so evidence from one exercise informs similar ones. α was tuned on separate
simulated students (live 0.6, hybrid 0.3). On the reported cohort it finds the
best exercise more often (52% vs 39%) with similar regret. On two larger
cohorts (200 students each) it again found the best exercise more often
(56% vs 44%, 52% vs 49%) but its regret was 4–5% *higher* (281 vs 267,
274 vs 263), so it is reported as a candidate and not switched on. That is an honest, defensible
result: better at finding the best exercise, slightly costlier exploration.

**Screening severity (integration with Components 1–3):** `POST
/api/v1/therapy/screening` with `{user_id, severity}`. Severe/moderate start at
Beginner, mild at Intermediate (only before the first reading, and never over
a therapist's choice). Exercises recommended for that severity get +0.15 on
their UCB score, and the others −0.15. With no history every UCB is equal, so the
screening decides the first plan: severe → Beginner reading + gentle pacing +
DAF; mild → Intermediate reading + standard pacing + picture description. As
the student's own scores accumulate, they outweigh the 0.15.

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
* Every noisy value goes through `privacy.privatize_statistic()`, and each
  release is recorded with `budget_ledger.spend()`.

**What to claim, exactly:** "Differential privacy is applied to every statistic
that leaves the clinic." Do **not** say stored data is privatised. The
student and their therapist see exact results by design, protected by access
control. DP-SGD for federated training is **future work** (`federated_stub.py`
is a design only, labelled so in the app).

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
* Login rate limit: 5 wrong passwords for one account within 15 minutes →
  further attempts get HTTP 429 until the oldest failure expires.
* Audit log (`audit.py`, `data/audit_log.jsonl`): every therapist change
  (assignments, level, goals, notes, ratings, plan reviews), screening results
  and account deletions, with who and when. `GET /api/v1/therapist/audit`.
* Input validation: Pydantic models with bounds on every request body.

### 3.9 Consent and data rights (`account_data.py`)

* Sign-up requires ticking a consent statement (what is stored, voice never
  recorded, the right to download or delete, guardian agreement for under-18s).
  The consent version and time are saved on the account.
* Privacy tab → **Download my data** (everything stored, as JSON) and **Delete
  my account**. Deletion removes the account, records (and ratings on them),
  settings, plan reviews and survey response, then re-fits the calibration.
  This covers access and erasure under Sri Lanka's Personal Data Protection Act
  No. 9 of 2022.
* Future work: a separate parent/guardian account linked to a child's account.

### 3.10 Clinical measure: %SS (`scoring.py`)

The score's features (voicing, pauses, volume, speed) measure *practice
quality*, not stuttering itself. They don't detect repetitions,
prolongations or blocks. If a teammate's ASR / disfluency detector sends
`disfluencies` (a count) with a result, the score adds
**%SS = disfluencies / syllables × 100**, the standard clinical measure, at a
starting weight of −3 points per %SS. That weight is re-estimated from expert
ratings like every other weight. Without a count, the feature is 0 and nothing
changes.

---

## 3b. The therapy and adaptive learning, explained simply

**The approach is fluency shaping:** teach a slower, smoother, controlled way
of speaking, and practise it until it becomes natural.

* **Breathing warm-up:** relaxed breathing lowers tension; many blocks start
  with a tight breath or throat.
* **Pacing:** rate control. Words are highlighted at a target speed; slower
  speech gives the speech muscles time. The speed is personal (±10% per
  result, kept within 70–130%).
* **Graded reading (Beginner → Intermediate → Advanced):** the therapy
  *hierarchy*. Master easy speech first, then raise the difficulty.
* **Picture description:** spontaneous speech, the step towards real
  conversation (harder than reading aloud).
* **DAF:** your voice is played back about 50–100 ms late, which slows speech and
  reduces stuttering for many people. The delay is calibrated per user.
* **Real-time feedback:** "Take your time", "a little louder", "nice and
  steady", coached like a therapist would.

**One line for the viva:** *"The therapist teaches the technique in the
clinic. SpeakFree provides daily structured home practice with feedback and
sends the results back to the therapist."* It is a therapy **assistant**, not a
replacement.

**Three layers of adaptation:**

1. **Level staircase (1-up / 2-down):** one strong attempt unlocks the next
   level; two difficult ones in a row step back. This is the staircase method used
   in hearing tests, made quicker to climb so students aren't held back, and
   slower to drop so one bad day doesn't move anyone down. It keeps practice
   neither boring nor stressful.
2. **Speed:** +10% after a strong attempt, −10% after a difficult one.
3. **Weekly plan (LinUCB):** for each exercise it predicts the score plus an
   uncertainty bonus for rarely tried ones, and picks the highest total.
   *Analogy:* at a restaurant you mostly order the dish you know is good, but
   sometimes try a new one in case it's even better.

---

## 3c. Gaps an examiner may raise, and the honest answer

| Gap | Status |
|---|---|
| Differential privacy "not used" | Applied to every statistic leaving the clinic (cohort report, via `privatize_statistic`). Not applied to the student's own or the treating therapist's exact view, by design. Wording in the app corrected. |
| Federated learning | Design only. Presented as **future work**. |
| Integration with Components 1–3 | `POST /api/v1/therapy/screening`: severity sets the starting level and the first plan; severity tags on exercises now differ. The therapist can also enter it. Still to do: call it from the Component 1 screening page; the biomarker endpoint is not yet used by the frontend. |
| Score measures voice activity, not stuttering | %SS feature ready (§3.10); needs the disfluency count from a teammate's detector. |
| JSON-file storage | Known limitation: move to SQLite/PostgreSQL with SQLAlchemy (future work). |
| Not deployed | Future work: backend on Render/Railway, frontend on Vercel, HTTPS. |
| Phone use / reminders | Future work: installable PWA, daily reminders. |
| Real users | Run a 2-week pilot with 5–10 users: first-week vs last-week score, and SUS (§3.7). |

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

**Important:** the demo's ratings are **synthetic data for pipeline testing**
(see §2.1). The evidence page labels them as synthetic and keeps them apart
from real results. For the final report, follow the protocol in §2.2.

### Packaging the submission

Don't zip the working folder. It contains `backend/data/` (accounts, the
token-signing key `auth_secret.key`), `.env` and `venv/`. All of these are
gitignored, so build the zip from git instead (from the repository root):

```powershell
git archive --format=zip -o speakfree-component4.zip HEAD
```

This contains only committed files. Commit your changes first.

### 3-minute demo script (assistant + adaptive learning first)

1. **(0:00) Student `amal@demo.local` → My Progress.** Read the report card
   aloud: traffic light, one sentence, *This week*, *Next step*. Point at the
   level timeline ("Beginner → Intermediate on … after 1 strong Beginner reading").
   Open *Details* only to show the charts are still there.
2. **(0:40) Weekly Plan.** Read *Why this plan for you?*: level, recent
   average, trend, comfort. Then one item: "expects about 68, fairly sure,
   ranked #1 of 9".
3. **(1:10) Assistant.** Ask "What should I practise next?" and "Why did I get
   this score?". Show the intent/confidence tag.
4. **(1:40) Therapist `dr.silva@demo.local` → Compare students** (Kasun vs
   Ravi): different level, timeline, plan, reading speed and assistant answer
   to the same question. *"Same engine, different history, different output."*
5. **(2:20) Model evidence.** §1: clinician vs synthetic split, MAE / r /
   within ±15, strong-vs-4–5, kappa. §4: % plans judged appropriate.
6. **(2:50) Student page → Print / save PDF report** — the take-home report
   for a therapist or parent.

---

## 5. Likely questions

**Aren't your expert ratings simulated?** The seeded ones are, and they are
labelled *synthetic data for pipeline testing* in the code, the database
(`source: "synthetic"`) and on the evidence page. They are never mixed with
clinician ratings: once any clinician rating exists, the model fits only on
clinician ratings. The validation figures in the report are the clinician ones.

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
