"""
SO3 - Adaptive Weekly Planning Engine.

A working LinUCB contextual bandit, one per user. Each user's model is
rebuilt by replaying their own practice history (context at the time of
each attempt -> reward = that attempt's score / 100), so the plan adapts
to the individual and needs no separate model storage.

For every candidate exercise the bandit estimates
    expected reward  = θᵀx                  (what it predicts the score will be)
    uncertainty      = α·sqrt(xᵀA⁻¹x)       (how unsure it is — large if rarely tried)
and ranks by expected + uncertainty (the "upper confidence bound"). This
balances exploiting exercises that work for the student with exploring
ones it knows little about. Both numbers are returned so every
recommendation is explainable.

Therapist-assigned exercises are always placed first.
"""

import numpy as np

from app.therapy.adaptive import LEVELS, level_state
from app.therapy.exercises import EXERCISE_BANK, get_exercise

CONTEXT_DIM = 5  # [bias, level, avg_score, trend, comfort]
PLAN_SIZE = 3
ALPHA = 0.6


class LinUCBBandit:
    def __init__(self, n_arms: int, context_dim: int = CONTEXT_DIM, alpha: float = ALPHA):
        self.n_arms = n_arms
        self.alpha = alpha
        self.A = [np.identity(context_dim) for _ in range(n_arms)]
        self.b = [np.zeros(context_dim) for _ in range(n_arms)]
        self.pulls = [0] * n_arms

    def estimate(self, arm: int, context: np.ndarray) -> tuple[float, float]:
        """(expected reward, confidence bonus) for one arm."""
        A_inv = np.linalg.inv(self.A[arm])
        theta = A_inv @ self.b[arm]
        mean = float(theta @ context)
        bonus = self.alpha * math_sqrt(context @ A_inv @ context)
        return mean, bonus

    def arm_score(self, arm: int, context: np.ndarray) -> float:
        mean, bonus = self.estimate(arm, context)
        return mean + bonus

    def update(self, arm: int, context: np.ndarray, reward: float) -> None:
        self.A[arm] += np.outer(context, context)
        self.b[arm] += reward * context
        self.pulls[arm] += 1


def math_sqrt(x: float) -> float:
    return float(np.sqrt(max(x, 0.0)))


def build_context(records: list[dict], override: dict | None = None) -> np.ndarray:
    level_index = level_state(records, override)["level_index"]
    recent = [r["score"] for r in records[-5:]]
    avg_score = (sum(recent) / len(recent) / 100) if recent else 0.5
    last3 = [r["score"] for r in records[-3:]]
    prev3 = [r["score"] for r in records[-6:-3]]
    trend = (
        (sum(last3) / len(last3) - sum(prev3) / len(prev3)) / 100 if last3 and prev3 else 0.0
    )
    ratings = [r["self_rating"] for r in records[-5:]]
    comfort = (sum(1 for x in ratings if x != "hard") / len(ratings)) if ratings else 0.5
    return np.array(
        [1.0, level_index / (len(LEVELS) - 1), avg_score, max(-1.0, min(1.0, trend)), comfort],
        dtype=float,
    )


def train_user_bandit(records: list[dict]) -> LinUCBBandit:
    arm_index = {ex.id: i for i, ex in enumerate(EXERCISE_BANK)}
    bandit = LinUCBBandit(n_arms=len(EXERCISE_BANK))
    for i, record in enumerate(records):
        arm = arm_index.get(record["exercise_id"])
        if arm is None:
            continue
        bandit.update(arm, build_context(records[:i]), record["score"] / 100)
    return bandit


def _reason(exercise, records: list[dict], level: dict) -> str:
    attempts = [r for r in records if r["exercise_id"] == exercise.id]
    if exercise.level is not None:
        prefix = "Level set by your therapist. " if level.get("set_by_therapist") else ""
        return f"{prefix}Your current reading level is {level['label']}. {level['progress_text']}"
    if not attempts:
        return "New for you — let's see how it suits you."
    last = attempts[-1]
    if last["score"] >= level["strong_threshold"]:
        return f"You scored {last['score']} last time — keep building on it."
    if last["self_rating"] == "hard":
        return "This felt hard last time. A little more practice will make it easier."
    return f"Last score {last['score']} — a good one to practise again."


def _item(ex, source: str, reason: str, estimate: tuple[float, float] | None, pulls: int) -> dict:
    item = {
        "id": ex.id,
        "title": ex.title,
        "type": ex.type.value,
        "difficulty": ex.difficulty,
        "source": source,
        "reason": reason,
        "times_practised": pulls,
        "predicted_score": None,
        "uncertainty": None,
    }
    if estimate is not None:
        mean, bonus = estimate
        item["predicted_score"] = int(round(max(0.0, min(1.0, mean)) * 100)) if pulls else None
        item["uncertainty"] = int(round(bonus * 100))
    return item


def recommend_weekly_plan(
    records: list[dict], settings: dict | None = None, plan_size: int = PLAN_SIZE
) -> dict:
    """Plan for one user: therapist-assigned exercises first, then their
    current reading level, then the highest-UCB exercises of other types."""
    settings = settings or {}
    override = settings.get("level_override")
    level = level_state(records, override)
    context = build_context(records, override)
    bandit = train_user_bandit(records)
    arm_index = {ex.id: i for i, ex in enumerate(EXERCISE_BANK)}
    target_difficulty = level["level_index"] + 1

    chosen: list[dict] = []
    used_ids: set[str] = set()
    used_types: set[str] = set()

    for assignment in settings.get("assigned", []):
        ex = get_exercise(assignment["exercise_id"])
        if ex is None or ex.id in used_ids:
            continue
        arm = arm_index[ex.id]
        chosen.append(
            _item(ex, "therapist", "Assigned by your therapist.", bandit.estimate(arm, context), bandit.pulls[arm])
        )
        used_ids.add(ex.id)
        used_types.add(ex.type.value)

    reading = next(
        ex for ex in EXERCISE_BANK if ex.level is not None and ex.level.value == level["level"]
    )
    if reading.id not in used_ids:
        arm = arm_index[reading.id]
        chosen.append(
            _item(reading, "level", _reason(reading, records, level), bandit.estimate(arm, context), bandit.pulls[arm])
        )
        used_ids.add(reading.id)
        used_types.add(reading.type.value)

    candidates = []
    for i, ex in enumerate(EXERCISE_BANK):
        if ex.level is not None or ex.id in used_ids:
            continue
        mean, bonus = bandit.estimate(i, context)
        level_fit = -0.1 * abs(ex.difficulty - target_difficulty)
        candidates.append((mean + bonus + level_fit, ex, (mean, bonus), bandit.pulls[i]))
    candidates.sort(key=lambda c: c[0], reverse=True)

    for _, ex, estimate, pulls in candidates:
        if len(chosen) >= max(plan_size, len(settings.get("assigned", [])) + 1):
            break
        if ex.type.value in used_types:
            continue
        chosen.append(_item(ex, "bandit", _reason(ex, records, level), estimate, pulls))
        used_types.add(ex.type.value)

    return {
        "level": level,
        "exercises": chosen,
        "context": {
            "level": round(float(context[1]), 2),
            "recent_average": round(float(context[2]) * 100),
            "trend": round(float(context[3]) * 100),
            "comfort": round(float(context[4]) * 100),
        },
    }
