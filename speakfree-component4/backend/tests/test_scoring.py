import numpy as np

from app.therapy import scoring
from app.therapy.progress_store import add_record


def attempt(**kw):
    base = {
        "duration_seconds": 60,
        "speaking_ratio": 0.7,
        "long_pauses": 0,
        "quiet_warnings": 0,
        "self_rating": "ok",
    }
    return {**base, **kw}


def test_breakdown_adds_up_to_score():
    score, parts = scoring.score_with_breakdown(attempt(long_pauses=2))
    assert score == round(sum(p["points"] for p in parts))


def test_more_pauses_lower_score():
    smooth, _ = scoring.score_with_breakdown(attempt(long_pauses=0))
    bumpy, _ = scoring.score_with_breakdown(attempt(long_pauses=4))
    assert bumpy < smooth


def test_rate_deviation_penalised():
    on_target, _ = scoring.score_with_breakdown(attempt(measured_wpm=100, target_wpm=100))
    too_fast, _ = scoring.score_with_breakdown(attempt(measured_wpm=160, target_wpm=100))
    assert too_fast < on_target


def test_score_is_clipped():
    score, _ = scoring.score_with_breakdown(attempt(speaking_ratio=1.0, self_rating="easy"))
    assert 0 <= score <= 100


def test_prior_used_until_enough_ratings():
    cal = scoring.calibrate()
    assert cal["active"] == "prior"
    assert cal["weights"] == scoring.PRIOR_WEIGHTS


def test_calibration_learns_from_expert_ratings():
    """Experts here care much more about long pauses than the prior assumes;
    the calibrated model should move towards that and predict them better."""
    rng = np.random.default_rng(0)
    for i in range(40):
        pauses = int(rng.integers(0, 6))
        ratio = float(rng.uniform(0.4, 0.9))
        expert_score = np.clip(90 - 18 * pauses + 20 * (ratio - 0.65), 0, 100)
        rating = int(np.clip(round(expert_score / 25 + 1), 1, 5))
        add_record(
            f"s{i % 5}@x.com",
            {
                **attempt(long_pauses=pauses, speaking_ratio=ratio),
                "exercise_id": "reading-beginner",
                "exercise_type": "reading",
                "title": "t",
                "score": 70,
                "expert": {"rating": rating},
            },
        )
    cal = scoring.calibrate()
    assert cal["active"] == "calibrated"
    assert cal["weights"]["pauses_per_min"] < scoring.PRIOR_WEIGHTS["pauses_per_min"]
    v = cal["validation"]
    assert v["calibrated_model_loo"]["mae"] < v["prior_model"]["mae"]


def test_thresholds_fall_back_with_one_class():
    pred = np.array([50.0, 60.0, 70.0])
    t, acc = scoring._best_threshold(pred, np.array([True, True, True]), 75)
    assert (t, acc) == (75, None)
