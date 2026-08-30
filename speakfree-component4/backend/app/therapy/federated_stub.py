"""
SO4 - Federated Learning Infrastructure (ARCHITECTURE STUB).

This is intentionally NOT a running federated learning system — that
requires multiple real client devices, real accumulated session
gradients, and a live aggregation server, none of which exist for a
single-machine demo. This module documents the intended design
(matching the proposal's Flower/FedAvg architecture) and exposes an
endpoint that returns that design as data, so the dashboard can show
"how it would work" honestly rather than faking live training.
"""

FEDERATED_ARCHITECTURE = {
    "protocol": "FedAvg with secure aggregation",
    "framework": "Flower (flwr)",
    "round_frequency": "weekly",
    "compression": "top-k sparsification (k=10%) + 16-bit quantisation",
    "payload_size_target_mb": 3,
    "raw_audio_leaves_device": False,
    "aggregation_weighting": "by sessions completed per client that week",
    "status": "design-complete, not deployed — requires multi-device rollout",
}


def get_federated_architecture() -> dict:
    return FEDERATED_ARCHITECTURE
