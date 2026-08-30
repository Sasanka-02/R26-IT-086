"""
SO3 - Adaptive Weekly Planning Engine.

A working (simplified) LinUCB contextual bandit. Real math, real
online updates — scaled down from the proposal's 48-exercise catalogue
to a manageable demo set, and using an in-memory model instead of a
persisted one. This genuinely selects exercises based on context and
learns from reward signals; it is not decorative.
"""

import numpy as np

EXERCISE_CATALOGUE = [
    {"id": "ex-pacing-gentle", "title": "Gentle Pacing Practice", "difficulty": 1},
    {"id": "ex-pacing-standard", "title": "Standard Pacing Practice", "difficulty": 2},
    {"id": "ex-onset-soft", "title": "Soft Onset Drills", "difficulty": 1},
    {"id": "ex-daf-short", "title": "DAF — Short Delay", "difficulty": 2},
    {"id": "ex-daf-long", "title": "DAF — Extended Delay", "difficulty": 3},
    {"id": "ex-conversation", "title": "Guided Conversation Practice", "difficulty": 3},
]

CONTEXT_DIM = 4  # [severity_level, avg_stutter_freq, trend, comfort_score]


class LinUCBBandit:
    def __init__(self, n_arms: int, context_dim: int = CONTEXT_DIM, alpha: float = 1.0):
        self.n_arms = n_arms
        self.alpha = alpha
        self.A = [np.identity(context_dim) for _ in range(n_arms)]
        self.b = [np.zeros(context_dim) for _ in range(n_arms)]

    def select_arm(self, context: np.ndarray) -> int:
        scores = []
        for arm in range(self.n_arms):
            A_inv = np.linalg.inv(self.A[arm])
            theta = A_inv @ self.b[arm]
            mean = theta @ context
            confidence = self.alpha * math_sqrt(context @ A_inv @ context)
            scores.append(mean + confidence)
        return int(np.argmax(scores))

    def update(self, arm: int, context: np.ndarray, reward: float) -> None:
        self.A[arm] += np.outer(context, context)
        self.b[arm] += reward * context


def math_sqrt(x: float) -> float:
    return float(np.sqrt(max(x, 0.0)))


_bandit = LinUCBBandit(n_arms=len(EXERCISE_CATALOGUE))


def build_context(
    severity_level: int, avg_stutter_freq: float, trend: float, comfort_score: float
) -> np.ndarray:
    return np.array([severity_level, avg_stutter_freq, trend, comfort_score], dtype=float)


def recommend_weekly_plan(context: np.ndarray, plan_size: int = 3) -> list[dict]:
    """Selects `plan_size` distinct exercises for the coming week."""
    chosen_indices: list[int] = []
    for _ in range(min(plan_size, len(EXERCISE_CATALOGUE))):
        arm = _bandit.select_arm(context)
        while arm in chosen_indices:
            arm = (arm + 1) % len(EXERCISE_CATALOGUE)
        chosen_indices.append(arm)
    return [EXERCISE_CATALOGUE[i] for i in chosen_indices]


def record_week_outcome(exercise_id: str, context: np.ndarray, reward: float) -> None:
    """Feeds back the relative reduction in stuttering frequency (the
    proposal's reward signal) so the bandit updates for next week."""
    for i, ex in enumerate(EXERCISE_CATALOGUE):
        if ex["id"] == exercise_id:
            _bandit.update(i, context, reward)
            return
