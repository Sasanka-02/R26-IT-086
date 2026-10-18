# SpeakFree – Component 4: Adaptive Therapy Plans & AI Therapy Assistant

Runs inside the integrated backend. Input: the Component 3 report (+ C1/C2 numbers).
Output: a patient-safe adaptive plan, scored practice sessions and a category-aware AI assistant.
Patient pages: **Therapy Plan**, **Exercise session**, **AI Assistant**. Admin page: **Therapy monitor**.

## ★ Novelty 1 – category-specific adaptive therapy

| C3 disorder | Focus (`categories.py`) | Ladder family | Patient sees |
|---|---|---|---|
| stuttering | fluency | graded reading + pacing + DAF | “Smooth, confident speech” |
| dysarthria | motor_speech | clear speech + loudness + breath support | “A clear, strong voice” |
| articulation | speech_sounds | sound drills generated for the sounds C1 flagged | “Crisp speech sounds” |
| normal | maintenance | reading + picture talk | “Keep your speech sharp” |

`plan.py → build_plan(profile, attempts)` closes the loop C1 → C2 → C3 → C4 → practice → C4:

1. **Focus** from the C3 disorder · 2. **Dose** from C3 severity (L4: 6×10 min … L1: 3×10 min) ·
3. **Starting level** from severity (L3–4 Beginner, L2 Intermediate, L1 Advanced) ·
4. **Content**: sound drills for C1's flagged sounds · 5. **Ranking** by the bandit (below) ·
6. **Goals** from C1/C2/C3 numbers and the patient's own attempts ·
7. **Re-screening** after 14 days, 12 exercises or a mastered ladder – the new screening re-anchors the plan.

### Adaptive engine (`bandit.py`)
```
context x = [1, level, avg_score, trend, comfort, C3 severity, C3 confidence]
LinUCB per exercise j:  A_j = I + Σ x xᵀ,  b_j = Σ r x,  θ_j = A_j⁻¹ b_j        (reward = score / 100)
UCB_j     = θ_jᵀ x + α √(xᵀ A_j⁻¹ x)                                                   α = 0.6
C3 prior  = β (2 · Σ_c P_C3(c) · 1[j targets c] − 1)                                  β = 0.2
rank by     UCB_j + prior_j − 0.1 · |difficulty_j − (level + 1)|
```
With no history the C3 prior decides the first plan. As the patient's own scores accumulate, they
outweigh the prior. **Level ladder** (`adaptive.py`): 2 strong attempts in a row move the patient
up, 2 difficult ones move them down, and passage speed adapts ±10 % per attempt.
**Attempt score** (`scoring.py`): an explainable linear model over voicing, pauses, loudness warnings,
rate deviation, self-rating, duration and exercise-goal completion.

## ★ Novelty 2 – category-aware AI assistant (`assistant.py`)
Naive-Bayes intent classifier (23 intents, leave-one-out ≈ 82 %) → answers from the patient's
own plan, goals and scores using **their focus's** tips (e.g. the exact flagged sound). If the
classifier isn't confident, an optional Claude model (`llm.py`, set `ANTHROPIC_API_KEY`) answers
with a focus-specific system prompt and only a small summary of the patient's practice numbers.
Otherwise a safe fallback answers. It never names a disorder or severity level.

## Live coaching (`realtime_feedback.py`)
The browser computes loudness, voicing and syllable peaks every 500 ms and streams only those
numbers to `/ws/therapy-live/{id}`. The server replies with coaching messages and builds the
attempt summary (incl. longest steady voicing for the breath task).

## Tests
```powershell
..\..\speakfree-component1\backend\venv\Scripts\python -m pytest -q    # from speakfree-component4\backend
```

## Carried over from the stand-alone prototype
- **Patient dashboard** (`dashboard.py`): traffic-light report card, highlights, badges, weekly table,
  first try vs latest, and "why this plan" in words with the planner's expected score + confidence.
- **Extra practice** (`extra_exercises.py`): picture-card **word ladder** for ages 6–11 (7 word levels +
  3 phrase stages, `adaptive.word_state`), **role-plays** for ages 12+, teen/adult picture scenes, kids' pacing.
- **Therapist controls** (`therapist.py`, platform tables from migration 0005): homework with due dates,
  measurable goals, shared / private clinical notes, alerts, 1–5 attempt ratings, plan reviews.
- **Evidence** (`evaluation.py`): score-vs-therapist agreement (MAE, r) with a ridge recalibration
  (leave-one-out, reported as a proposal), weighted kappa, plan-review stats, System Usability Scale.
- **Privacy** (`privacy.py`): Laplace-mechanism cohort report with a persisted ε budget ledger,
  DAF calibration (5 delay trials), federated learning as a documented design only.

The prototype's own login system and therapist portal are replaced by the platform's accounts and admin.
