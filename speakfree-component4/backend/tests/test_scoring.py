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


def _rated(rating, source, by="dr@clinic.lk", second=None):
    rec = {"id": f"r{np.random.randint(1e9)}", "completed_at": "2026-10-01T10:00:00+00:00",
           "title": "t", "exercise_type": "reading", "score": 60,
           "expert": {"rating": rating, "by": by, "source": source}, **attempt()}
    if second is not None:
        rec["expert_reviews"] = {by: rec["expert"], "dr2@clinic.lk": {"rating": second, "by": "dr2@clinic.lk"}}
    return rec


def test_synthetic_ratings_are_kept_apart_from_clinician_ratings():
    for i in range(10):
        add_record("s@x.com", _rated(1 + i % 5, "synthetic", by="dr.silva@demo.local"))
    cal = scoring.calibrate()
    assert cal["data_source"] == "synthetic"
    assert cal["n_synthetic"] == 10 and cal["n_clinician"] == 0

    add_record("s@x.com", _rated(4, "clinician"))
    cal = scoring.calibrate()
    # One real rating replaces the synthetic pool: too few to calibrate, so the prior is used.
    assert cal["data_source"] == "clinician"
    assert cal["n_ratings"] == 1 and cal["active"] == "prior"
    assert cal["validation_by_source"]["synthetic"]["n"] == 10


def test_unlabelled_demo_ratings_count_as_synthetic():
    assert scoring.rating_source({"rating": 3, "by": "dr.silva@demo.local"}) == "synthetic"
    assert scoring.rating_source({"rating": 3, "by": "slp@hospital.lk"}) == "clinician"


def test_cohen_kappa():
    assert scoring.cohen_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == 1.0
    assert scoring.cohen_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], weighted=True) == 1.0
    near = scoring.cohen_kappa([1, 2, 3, 4, 5], [2, 2, 3, 4, 4], weighted=True)
    far = scoring.cohen_kappa([1, 2, 3, 4, 5], [5, 4, 3, 2, 1], weighted=True)
    assert near > 0.7 > far


def test_inter_rater_agreement_reported():
    for a, b in [(4, 4), (3, 4), (2, 2), (5, 5), (1, 2)]:
        add_record("s@x.com", _rated(a, "clinician", second=b))
    v = scoring.calibrate()["validation"]
    assert v["inter_rater"]["n_pairs"] == 5
    assert v["inter_rater"]["exact_agreement"] == 60
    assert v["strong_match"]["n"] == 5
