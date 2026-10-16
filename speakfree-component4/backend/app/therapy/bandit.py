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

from app.therapy.adaptive import LEVELS, level_state, word_level_state
from app.therapy.exercises import EXERCISE_BANK, get_exercise

CONTEXT_DIM = 5  # [bias, level, avg_score, trend, comfort]
PLAN_SIZE = 3
ALPHA = 0.6
# Added to an exercise's UCB when it is recommended for the student's screening
# severity (subtracted when it is not). With no history every UCB is equal, so
# this decides the first plan; as evidence builds up, the student's own scores
# dominate.
SEVERITY_BONUS = 0.15


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


EXERCISE_TYPES = ["reading", "pacing", "daf", "picture", "words"]


def exercise_features(ex) -> np.ndarray:
    """[1, difficulty, difficulty², type one-hot] — what the exercise is like."""
    d = ex.difficulty / 3
    return np.array([1.0, d, d * d] + [1.0 if ex.type.value == t else 0.0 for t in EXERCISE_TYPES])


class HybridLinUCB:
    """LinUCB that also uses exercise features (evaluated in simulation only).

    One ridge model over z = [student context ⊗ exercise features, exercise
    one-hot]. The shared part lets evidence from one exercise inform similar
    ones (same type, nearby difficulty); the one-hot keeps a per-exercise
    offset. Compared with the per-exercise model on the evidence page."""

    def __init__(self, n_arms: int, context_dim: int = CONTEXT_DIM, alpha: float = 0.3):
        self.features = [exercise_features(ex) for ex in EXERCISE_BANK[:n_arms]]
        self.n_arms = n_arms
        self.alpha = alpha
        dim = context_dim * len(self.features[0]) + n_arms
        self.A = np.identity(dim)
        self.b = np.zeros(dim)

    def _z(self, arm: int, context: np.ndarray) -> np.ndarray:
        onehot = np.zeros(self.n_arms)
        onehot[arm] = 1.0
        return np.concatenate([np.outer(context, self.features[arm]).ravel(), onehot])

    def choose(self, context: np.ndarray) -> int:
        A_inv = np.linalg.inv(self.A)
        theta = A_inv @ self.b
        scores = []
        for arm in range(self.n_arms):
            z = self._z(arm, context)
            scores.append(theta @ z + self.alpha * math_sqrt(z @ A_inv @ z))
        return int(np.argmax(scores))

    def update(self, arm: int, context: np.ndarray, reward: float) -> None:
        z = self._z(arm, context)
        self.A += np.outer(z, z)
        self.b += reward * z


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
    if exercise.word_level is not None:
        return f"Your word level. {word_level_state(records)['progress_text']}"
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


def _sureness(uncertainty: int | None) -> str:
    if uncertainty is None or uncertainty > 60:
        return "still unsure"
    if uncertainty > 30:
        return "fairly sure"
    return "quite sure"


def _explain_context(records: list[dict], level: dict, context: np.ndarray) -> list[str]:
    """The numbers the bandit plans from, said in words."""
    lines = [f"You are on {level['label']} reading. {level['progress_text']}"]
    if not records:
        lines.append(
            "You haven't saved any exercises yet, so the engine starts from neutral guesses "
            "and will try a bit of everything first."
        )
        return lines
    recent = records[-5:]
    lines.append(f"Your last {len(recent)} score{'s' if len(recent) != 1 else ''} average {round(context[2] * 100)} out of 100.")
    trend = round(context[3] * 100)
    if len(records) >= 6:
        if trend >= 5:
            lines.append(f"Your scores are rising (up {trend} points), so the plan can stretch you a little.")
        elif trend <= -5:
            lines.append(f"Your scores dipped by {-trend} points, so the plan leans towards exercises that work for you.")
        else:
            lines.append("Your scores are steady.")
    comfortable = sum(1 for r in recent if r["self_rating"] != "hard")
    lines.append(f"{comfortable} of your last {len(recent)} exercises felt okay or easy to you.")
    return lines


def _explain_item(item: dict, level: dict) -> str:
    if item["source"] == "therapist":
        return "Your therapist assigned this, so it always comes first."
    if item["source"] == "words":
        return (
            f"This is your word level ({item['title'].split(' — ')[0]}). "
            "One good round here moves you up the word ladder."
        )
    if item["source"] == "level":
        if level["mastered"]:
            return "You have completed the final stage — this passage keeps your reading fluent."
        goal = "move you up" if level["next_level"] else "complete the final stage"
        return (
            f"This is the passage for your level ({level['label']}). "
            f"One strong reading here will {goal}."
        )
    if item["predicted_score"] is None:
        return (
            f"You haven't tried this yet. The engine ranked it #{item['rank']} of {item['compared']} "
            "because trying it tells it whether it suits you."
        )
    return (
        f"From your {item['times_practised']} attempt{'s' if item['times_practised'] != 1 else ''}, the engine "
        f"expects you to score about {item['predicted_score']} here and is {_sureness(item['uncertainty'])}. "
        f"It ranked #{item['rank']} of the {item['compared']} exercises it compared for you."
    )


def recommend_weekly_plan(
    records: list[dict], settings: dict | None = None, plan_size: int = PLAN_SIZE
) -> dict:
    """Plan for one user: therapist-assigned exercises first, then their
    current reading level, then the highest-UCB exercises of other types."""
    settings = settings or {}
    override = settings.get("level_override")
    screening = settings.get("screening")
    severity = screening["severity"] if screening else None
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
        # Reading and word levels are placed by their own ladders, not the bandit.
        if ex.level is not None or ex.word_level is not None or ex.type.value == "words" or ex.id in used_ids:
            continue
        mean, bonus = bandit.estimate(i, context)
        level_fit = -0.1 * abs(ex.difficulty - target_difficulty)
        severity_fit = 0.0
        if severity not in (None, "unknown"):
            severity_fit = SEVERITY_BONUS if severity in ex.recommended_for else -SEVERITY_BONUS
        candidates.append((mean + bonus + level_fit + severity_fit, ex, (mean, bonus), bandit.pulls[i]))
    candidates.sort(key=lambda c: c[0], reverse=True)

    for rank, (_, ex, estimate, pulls) in enumerate(candidates, start=1):
        if len(chosen) >= max(plan_size, len(settings.get("assigned", [])) + 1):
            break
        if ex.type.value in used_types:
            continue
        item = _item(ex, "bandit", _reason(ex, records, level), estimate, pulls)
        item["rank"] = rank
        item["compared"] = len(candidates)
        chosen.append(item)
        used_types.add(ex.type.value)

    # Children's word ladder: the current word level is added (on top of the
    # bandit picks) for anyone who practises words or hasn't started reading.
    words = word_level_state(records)
    reads = any(r["exercise_type"] == "reading" for r in records)
    if (words["rounds"] or not reads) and words["exercise_id"] not in used_ids:
        word_ex = get_exercise(words["exercise_id"])
        arm = arm_index[word_ex.id]
        item = _item(word_ex, "words", _reason(word_ex, records, level), bandit.estimate(arm, context), bandit.pulls[arm])
        if words["rounds"] and not reads:
            # A child working on words: the word level is their main exercise,
            # so it comes first (after anything the therapist assigned).
            chosen.insert(sum(1 for c in chosen if c["source"] == "therapist"), item)
        else:
            chosen.append(item)
        used_ids.add(word_ex.id)

    for item in chosen:
        item["explanation"] = _explain_item(item, level)
        ex = get_exercise(item["id"])
        if item["source"] == "bandit" and severity not in (None, "unknown") and severity in ex.recommended_for:
            item["explanation"] += f" It suits {severity} stuttering (your screening result)."

    why = _explain_context(records, level, context)
    if screening:
        why.insert(
            1,
            f"Your screening result was {screening['severity']} stuttering ({screening['source']}), "
            "so the plan favours exercises suited to it.",
        )
    return {
        "level": level,
        "word_level": words,
        "exercises": chosen,
        "screening": screening,
        "why": why,
        "context": {
            "level": round(float(context[1]), 2),
            "recent_average": round(float(context[2]) * 100),
            "trend": round(float(context[3]) * 100),
            "comfort": round(float(context[4]) * 100),
        },
    }
