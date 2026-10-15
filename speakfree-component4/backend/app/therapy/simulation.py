"""
Offline evaluation of the adaptive planner (LinUCB) by simulation.

Each simulated student has a hidden "true benefit" for every exercise
(the reward that exercise would give them on average). Each round a
strategy picks one exercise, observes a noisy reward, and learns. We
compare:

  * LinUCB  — the contextual bandit used by the app (student features only)
  * LinUCB + exercise features — HybridLinUCB, which also knows each
    exercise's type and difficulty (candidate improvement, not yet live)
  * Random  — pick any exercise uniformly
  * Rotation — cycle through exercises in a fixed order (a typical static plan)

Metrics (averaged over students, fixed random seed so results reproduce):
  * average reward per round (higher is better)
  * cumulative regret: total reward lost versus always picking the
    student's best exercise (lower is better)
  * best-exercise rate: share of the final 10 rounds spent on the
    student's best exercise

α for each LinUCB variant was chosen on separate simulated students
(seeds 5000+), not on the students reported here.
"""

from functools import lru_cache


import numpy as np

from app.therapy.bandit import ALPHA, HybridLinUCB, LinUCBBandit
from app.therapy.exercises import EXERCISE_BANK

N_ARMS = len(EXERCISE_BANK)
HYBRID_ALPHA = 0.3


def _student(rng: np.random.Generator) -> dict:
    skill = rng.uniform(0.2, 0.9)
    difficulty = np.array([ex.difficulty for ex in EXERCISE_BANK], dtype=float)
    # Exercises near the student's skill help most; personal preference adds variety.
    fit = 1 - np.abs(difficulty / 3 - skill)
    preference = rng.normal(0, 0.12, N_ARMS)
    benefit = np.clip(0.35 + 0.45 * fit + preference, 0.05, 0.95)
    return {"skill": skill, "benefit": benefit}


def _context(skill: float, rewards: list[float]) -> np.ndarray:
    recent = rewards[-5:]
    avg = float(np.mean(recent)) if recent else 0.5
    trend = float(np.mean(rewards[-3:]) - np.mean(rewards[-6:-3])) if len(rewards) >= 6 else 0.0
    comfort = float(np.mean([r > 0.4 for r in recent])) if recent else 0.5
    return np.array([1.0, skill, avg, trend, comfort])


def _run(strategy: str, student: dict, rounds: int, rng: np.random.Generator) -> np.ndarray:
    bandit = LinUCBBandit(N_ARMS, alpha=ALPHA)
    hybrid = HybridLinUCB(N_ARMS, alpha=HYBRID_ALPHA)
    rewards: list[float] = []
    picks = np.empty(rounds, dtype=int)
    for t in range(rounds):
        x = _context(student["skill"], rewards)
        if strategy == "linucb":
            arm = int(np.argmax([bandit.arm_score(a, x) for a in range(N_ARMS)]))
        elif strategy == "hybrid":
            arm = hybrid.choose(x)
        elif strategy == "random":
            arm = int(rng.integers(N_ARMS))
        else:  # rotation
            arm = t % N_ARMS
        reward = float(np.clip(student["benefit"][arm] + rng.normal(0, 0.08), 0, 1))
        if strategy == "hybrid":
            hybrid.update(arm, x, reward)
        else:
            bandit.update(arm, x, reward)
        rewards.append(reward)
        picks[t] = arm
    return np.array(rewards), picks


@lru_cache(maxsize=4)
def evaluate(n_students: int = 60, rounds: int = 30, seed: int = 7) -> dict:
    """Deterministic (fixed seeds), so the result is cached."""
    strategies = {
        "linucb": "LinUCB (adaptive, in the app)",
        "hybrid": "LinUCB + exercise features",
        "random": "Random",
        "rotation": "Fixed rotation",
    }
    per_round = {s: np.zeros(rounds) for s in strategies}
    regret = {s: [] for s in strategies}
    best_rate = {s: [] for s in strategies}

    for i in range(n_students):
        student = _student(np.random.default_rng(seed + i))
        best_arm = int(np.argmax(student["benefit"]))
        best_value = student["benefit"][best_arm]
        for s in strategies:
            rng = np.random.default_rng(10_000 + seed + i)  # same noise for every strategy
            rewards, picks = _run(s, student, rounds, rng)
            per_round[s] += rewards
            expected = student["benefit"][picks]
            regret[s].append(float(np.sum(best_value - expected)))
            best_rate[s].append(float(np.mean(picks[-10:] == best_arm)))

    curves = [
        {"round": t + 1, **{s: round(float(per_round[s][t] / n_students) * 100, 1) for s in strategies}}
        for t in range(rounds)
    ]
    summary = [
        {
            "strategy": s,
            "label": label,
            "average_reward": round(float(np.mean([c[s] for c in curves])), 1),
            "final_10_reward": round(float(np.mean([c[s] for c in curves[-10:]])), 1),
            "cumulative_regret": round(float(np.mean(regret[s])) * 100, 1),
            "best_exercise_rate": round(float(np.mean(best_rate[s])) * 100),
        }
        for s, label in strategies.items()
    ]
    return {
        "students": n_students,
        "rounds": rounds,
        "seed": seed,
        "labels": strategies,
        "curves": curves,
        "summary": summary,
    }
