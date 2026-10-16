"""Component 2 tests: articulation-score formulas (worked examples) + session pipeline."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from component2.articulation_score import normalise_words, score_component1, word_errors  # noqa: E402
from component2.fluency_events import count_fluency_events  # noqa: E402
from component2.session_pipeline import run_component2  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
PICTURE = json.loads((SAMPLES / "component1_output_example.json").read_text(encoding="utf-8"))
READING = json.loads((SAMPLES / "component1_reading_example.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ formula alignment (novelty)
def test_r2_normalisation():
    assert normalise_words("Um, the cat’s TREE.") == ["um", "the", "cat's", "tree"]


def test_worked_example_method_b():
    # N = 10, M = 11 tokens, C = 9.35 / 11 = 0.85, L = 1, CWR = 0.9 -> 87.5, good
    result = score_component1(PICTURE)
    assert result["method"] == "B_confidence_clear_word_ratio"
    i = result["inputs"]
    assert (i["N_kept_words"], i["M_kept_tokens"], i["L_dysfluency_candidates"]) == (10, 11, 1)
    assert i["C_confidence"] == 0.85
    assert i["CWR_clear_word_ratio"] == 0.9
    assert result["articulation_score"] == 87.5
    assert result["articulation_level"] == "good"
    assert result["filler_count"] == 1
    assert result["reliability"] == "normal"


def test_worked_example_method_a():
    # N = 9, S = 1 (red -> wed), D = 0, I = 1 (repeated "sat") -> 100 x (1 - 2/9) = 77.78, fair
    result = score_component1(READING)
    assert result["method"] == "A_word_accuracy"
    i = result["inputs"]
    assert (i["N_reference_words"], i["S"], i["D"], i["I"]) == (9, 1, 0, 1)
    assert result["articulation_score"] == 77.78
    assert result["articulation_level"] == "fair"


def test_fillers_counted_by_component1_wer_but_not_ours():
    c1_words = normalise_words(READING["transcript"])
    assert word_errors(normalise_words(READING["reference_text"]), c1_words) == {
        "substitutions": 1, "deletions": 0, "insertions": 2, "correct": 8}


def test_reference_text_ignored_unless_reading():
    assert score_component1({**READING, "task_type": "picture"})["method"] == "B_confidence_clear_word_ratio"


def test_word_accuracy_clipped_at_zero():
    assert score_component1({**READING, "reference_text": "cat"})["articulation_score"] == 0.0


def test_r1_threshold_from_component1():
    c1 = copy.deepcopy(PICTURE)
    for seg in c1["word_segments"]:
        del seg["is_dysfluency_candidate"]
    c1["dysfluency_threshold"] = 0.92
    assert score_component1(c1)["inputs"]["L_dysfluency_candidates"] == 4


def test_fallback_overall_confidence_flagged():
    c1 = copy.deepcopy(PICTURE)
    for seg in c1["word_segments"]:
        del seg["tokens"]
    result = score_component1(c1)
    assert result["inputs"]["C_confidence"] == 0.8125
    assert "confidence_includes_fillers" in result["reliability_flags"]


def test_confidence_missing_uses_cwr_only():
    c1 = copy.deepcopy(PICTURE)
    for seg in c1["word_segments"]:
        del seg["tokens"]
    del c1["overall_confidence_percent"]
    result = score_component1(c1)
    assert result["articulation_score"] == 90.0
    assert "confidence_missing" in result["reliability_flags"]


def test_reliability_flags():
    c1 = copy.deepcopy(PICTURE)
    c1["acoustic_features"]["snr_db"] = 8
    c1["schema_version"] = "2.0.0"
    c1["word_segments"] = c1["word_segments"][:3]
    assert score_component1(c1)["reliability_flags"] == ["too_few_words", "noisy_recording", "schema_mismatch"]


def test_only_fillers_is_insufficient():
    result = score_component1({**PICTURE, "word_segments": [{"word": "Um,"}, {"word": "uh"}]})
    assert result["status"] == "insufficient_data"
    assert result["filler_count"] == 2


def test_invalid_probability_rejected():
    c1 = copy.deepcopy(PICTURE)
    c1["word_segments"][0]["tokens"][0]["probability"] = 95
    with pytest.raises(ValueError):
        score_component1(c1)


# ------------------------------------------------------------------ fluency events
def test_fluency_events_counts_repetitions_and_fillers():
    events = count_fluency_events(PICTURE)  # "the boy is um the boy is climbing on the tree"
    assert events["filler_count"] == 1
    assert events["word_repetition_count"] == 0
    c1 = {"word_segments": [{"word": w, "start": i, "end": i + 0.3} for i, w in enumerate("I I want the ball".split())]}
    assert count_fluency_events(c1)["word_repetition_count"] == 1


def test_prolongation_and_long_pause():
    c1 = {"word_segments": [{"word": "sssun", "start": 0.0, "end": 2.0}, {"word": "is", "start": 2.1, "end": 2.3}],
          "pauses": [{"start": 2.3, "end": 3.8, "duration": 1.5}, {"start": 4, "end": 4.3, "duration": 0.3}]}
    events = count_fluency_events(c1)
    assert events["prolongation_count"] == 1
    assert events["long_pause_count"] == 1


# ------------------------------------------------------------------ session pipeline (C2-Eq.5)
def _summary():
    return {"session_id": "s1", "patient_id": "SF-1", "age_bracket": 2, "overall_confidence_percent": 85.0,
            "dysfluency_ratio": 0.1, "fluency_score": 80, "pronunciation_score": 82, "phoneme_findings": [],
            "acoustic_summary": {"total_speech_sec": 30.0, "words_per_minute": 120}}


def test_session_score_is_word_weighted():
    short = copy.deepcopy(PICTURE)
    short["analysis_id"] = "short"
    short["word_segments"] = short["word_segments"][:4]  # the boy is um -> 3 kept words
    out = run_component2(_summary(), [PICTURE, short])
    pooled = out["session_articulation"]
    a_long = score_component1(PICTURE)["articulation_score"]
    a_short = score_component1(short)["articulation_score"]
    expected = (10 * a_long + 3 * a_short) / 13
    assert pooled["score"] == round(expected, 2)
    assert pooled["weights"] == [10, 3]
    assert out["ready_for_component3"] is True
    c3 = out["component3_input"]
    assert c3["articulation_score"] == pooled["score"]
    assert c3["component1"]["fluency_score"] == 80
    assert c3["fluency_events"]["filler_count"] == 2


def test_session_without_words_not_ready():
    out = run_component2(_summary(), [{**PICTURE, "word_segments": []}])
    assert out["ready_for_component3"] is False
    assert out["component3_input"] is None
