"""
SO5 - Differential Privacy Integration (demo-scale, genuinely functional).

Implements the Laplace mechanism for privatising stored session
statistics, and a per-patient privacy budget ledger. This is real,
working differential privacy math — not a stub — scaled down from the
full DP-SGD federated training loop described in the proposal (which
requires an actual training loop with real gradients to be meaningful).
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


def privatize_statistic(value: float, sensitivity: float, epsilon: float) -> float:
    """Adds calibrated Laplace noise to a single stored statistic
    (e.g. weekly stuttering frequency) before it is persisted."""
    return value + laplace_noise(sensitivity, epsilon)


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
