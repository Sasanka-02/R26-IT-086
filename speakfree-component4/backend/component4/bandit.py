"""
Adaptive exercise selection - a LinUCB contextual bandit conditioned on Component 3.

###########################################################################################
#  ★ COMPONENT 4 NOVELTY - SEVERITY-AWARE CONTEXTUAL BANDIT                               #
#                                                                                         #
#  Context (what the planner knows about the patient right now):                          #
#     x = [1, level, avg_score, trend, comfort, severity, c3_confidence]       (7-dim)     #
#        level         current ladder rung / 2                    (adaptive.py)           #
#        avg_score     mean of the last 5 attempt scores / 100                            #
#        trend         (mean last 3 - mean previous 3) / 100                              #
#        comfort       share of the last 5 attempts not rated "hard"                      #
#        severity      (C3 severity level - 1) / 3                                        #
#        c3_confidence C3 confidence score                                                #
#                                                                                         #
#  Per exercise j (arm), replayed from the patient's own attempts (reward = score / 100): #
#     A_j = I + Σ x xᵀ ,   b_j = Σ r x ,   θ_j = A_j⁻¹ b_j                                  #
#     UCB_j = θ_jᵀx  +  α·sqrt(xᵀ A_j⁻¹ x)                    (exploit + explore)          #
#                                                                                         #
#  Category prior from Component 3 (probability-weighted, not a hard filter):             #
#     fit_j   = Σ_c P_C3(c) · 1[exercise j targets focus c]                               #
#     prior_j = β · (2·fit_j − 1)            ∈ [−β, β]                                     #
#     diff_j  = −0.1 · |difficulty_j − (level + 1)|                                        #
#     rank by  UCB_j + prior_j + diff_j                                                    #
#                                                                                         #
#  With no history every UCB is equal, so the C3 prior decides the first plan; as the      #
#  patient's own scores accumulate, the evidence dominates - the plan adapts to the person #
#  and is re-anchored every time a new screening updates P_C3.                             #
###########################################################################################
"""
from __future__ import annotations

import numpy as np

from .adaptive import LEVELS

CONTEXT_DIM = 7
ALPHA = 0.6
CATEGORY_BETA = 0.20
DIFFICULTY_PENALTY = 0.10


class LinUCBBandit:
    def __init__(self, arm_ids: list[str], context_dim: int = CONTEXT_DIM, alpha: float = ALPHA):
        self.index = {a: i for i, a in enumerate(arm_ids)}
        self.alpha = alpha
        self.A = [np.identity(context_dim) for _ in arm_ids]
        self.b = [np.zeros(context_dim) for _ in arm_ids]
        self.pulls = [0] * len(arm_ids)

    def estimate(self, arm_id: str, x: np.ndarray) -> tuple[float, float]:
        i = self.index[arm_id]
        A_inv = np.linalg.inv(self.A[i])
        theta = A_inv @ self.b[i]
        return float(theta @ x), self.alpha * float(np.sqrt(max(x @ A_inv @ x, 0.0)))

    def update(self, arm_id: str, x: np.ndarray, reward: float) -> None:
        i = self.index.get(arm_id)
        if i is None:
            return
        self.A[i] += np.outer(x, x)
        self.b[i] += reward * x
        self.pulls[i] += 1


def build_context(records: list[dict], level_index: int, profile: dict) -> np.ndarray:
    recent = [r["score"] for r in records[-5:]]
    avg = (sum(recent) / len(recent) / 100) if recent else 0.5
    last3 = [r["score"] for r in records[-3:]]
    prev3 = [r["score"] for r in records[-6:-3]]
    trend = (sum(last3) / len(last3) - sum(prev3) / len(prev3)) / 100 if last3 and prev3 else 0.0
    ratings = [r["self_rating"] for r in records[-5:]]
    comfort = (sum(1 for x in ratings if x != "hard") / len(ratings)) if ratings else 0.5
    severity = (int(profile.get("severity_level") or 1) - 1) / 3
    confidence = float(profile.get("confidence") or 0.5)
    return np.array([1.0, level_index / (len(LEVELS) - 1), avg, max(-1.0, min(1.0, trend)), comfort,
                     severity, confidence], dtype=float)


def train(records: list[dict], arm_ids: list[str], profile: dict, ladder_levels: list[int]) -> LinUCBBandit:
    """Replay history: the context at the time of each attempt -> its reward."""
    bandit = LinUCBBandit(arm_ids)
    for i, r in enumerate(records):
        bandit.update(r["exercise_id"], build_context(records[:i], ladder_levels[i], profile), r["score"] / 100)
    return bandit


def category_fit(exercise: dict, focus_probs: dict[str, float]) -> float:
    return float(sum(p for focus, p in focus_probs.items() if focus in exercise.get("focus", [])))


def rank_arms(exercises: list[dict], records: list[dict], profile: dict, level: dict,
              ladder_levels: list[int]) -> tuple[list[dict], np.ndarray]:
    """Score every arm; returns (rows sorted best-first, context)."""
    arm_ids = [e["id"] for e in exercises]
    bandit = train(records, arm_ids, profile, ladder_levels)
    x = build_context(records, level["level_index"], profile)
    focus_probs = profile.get("focus_probabilities") or {profile.get("focus", "maintenance"): 1.0}
    target_difficulty = level["level_index"] + 1

    rows = []
    for ex in exercises:
        mean, bonus = bandit.estimate(ex["id"], x)
        fit = category_fit(ex, focus_probs)
        prior = CATEGORY_BETA * (2 * fit - 1)
        diff = -DIFFICULTY_PENALTY * abs(ex.get("difficulty", 1) - target_difficulty)
        pulls = bandit.pulls[bandit.index[ex["id"]]]
        rows.append({
            "id": ex["id"], "title": ex["title"], "type": ex["type"], "level": ex.get("level"),
            "difficulty": ex.get("difficulty", 1), "focus": ex.get("focus", []),
            "times_practised": pulls,
            "expected_reward": round(mean, 4),
            "exploration_bonus": round(bonus, 4),
            "category_fit": round(fit, 4),
            "category_prior": round(prior, 4),
            "difficulty_fit": round(diff, 4),
            "total": round(mean + bonus + prior + diff, 4),
            "predicted_score": int(round(max(0.0, min(1.0, mean)) * 100)) if pulls else None,
        })
    rows.sort(key=lambda r: r["total"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows, x
