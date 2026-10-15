"""
SO5 - Differential privacy: the Laplace mechanism and a privacy budget ledger.

Where it is applied (and where it is not):
  * Applied: every statistic that leaves the clinic. The cohort report
    (cohort_report.py) releases each count and mean through
    privatize_statistic() and records the ε spent in the budget ledger.
  * Not applied: the student's own dashboard and the treating therapist's
    view. They need exact numbers to give therapy, and they stay inside
    the clinic's access control (role checks on every endpoint).
  * Not implemented: DP-SGD inside federated training — see
    federated_stub.py; it is future work and labelled as such.
"""

import math
import random
from dataclasses import dataclass, field


def laplace_noise(sensitivity: float, epsilon: float) -> float:
    """Draws a single Laplace-distributed noise sample calibrated to
    (sensitivity, epsilon) for the Laplace mechanism."""
    scale = sensitivity / max(epsilon, 1e-9)
    u = random.uniform(-0.5, 0.5)
    return -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u) + 1e-12)


def privatize_statistic(value: float, sensitivity: float, epsilon: float, rng=None) -> float:
    """Laplace mechanism for one statistic: value + Lap(sensitivity / ε).
    Pass a numpy Generator to make a release reproducible (the cohort
    report caches releases so repeated requests cannot average noise away)."""
    if rng is None:
        return value + laplace_noise(sensitivity, epsilon)
    return value + float(rng.laplace(0.0, sensitivity / max(epsilon, 1e-9)))


@dataclass
class PrivacyBudgetLedger:
    """
    Tracks cumulative epsilon expenditure per patient. Once the budget
    threshold is reached, the ledger reports that the account should
    move to inference-only mode (per SO5's design).
    """
    epsilon_threshold: float = 10.0
    _spent: dict[str, float] = field(default_factory=dict)

    def spend(self, patient_id: str, epsilon: float) -> float:
        current = self._spent.get(patient_id, 0.0)
        updated = current + epsilon
        self._spent[patient_id] = updated
        return updated

    def remaining(self, patient_id: str) -> float:
        return max(0.0, self.epsilon_threshold - self._spent.get(patient_id, 0.0))

    def is_exhausted(self, patient_id: str) -> bool:
        return self._spent.get(patient_id, 0.0) >= self.epsilon_threshold

    def status(self, patient_id: str) -> dict:
        spent = self._spent.get(patient_id, 0.0)
        return {
            "patient_id": patient_id,
            "epsilon_spent": round(spent, 4),
            "epsilon_threshold": self.epsilon_threshold,
            "epsilon_remaining": round(self.remaining(patient_id), 4),
            "inference_only": self.is_exhausted(patient_id),
        }


budget_ledger = PrivacyBudgetLedger()
