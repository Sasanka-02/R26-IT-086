import copy
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from services.articulation_score import normalise_words, score_component1, word_errors
from services.component1_pipeline import process_component1_output
from services.component2_service import gloss_from_component1
from services.component3_client import send_to_component3
from services.pcc_scoring import score_pcc

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
PICTURE = json.loads((SAMPLES / "component1_output_example.json").read_text(encoding="utf-8"))
READING = json.loads((SAMPLES / "component1_reading_example.json").read_text(encoding="utf-8"))


def fake_audio_analysis(produced: str):
    words, unscored = gloss_from_component1(PICTURE)
    return {"articulation_analysis": score_pcc(words, produced.split(), unscored, "component1_transcript")}


# "the boy is um the boy is climbing on the tree", "um" and "climbing" are dysfluency candidates
PRODUCED = "ð ə b oɪ ɪ z ʌ m ð ə b oɪ ɪ z k l aɪ m ɪ ŋ ɑː n ð ə t w iː"


class FormulaAlignmentTests(unittest.TestCase):
    def test_r2_normalisation(self):
        self.assertEqual(normalise_words("Um, the cat’s TREE."), ["um", "the", "cat's", "tree"])

    def test_worked_example_6_1_method_b(self):
        # N = 10, M = 11 tokens, C = 9.35 / 11 = 0.85, L = 1, CWR = 0.9 -> 87.5, good
        result = score_component1(PICTURE)
        self.assertEqual(result["method"], "B_confidence_clear_word_ratio")
        i = result["inputs"]
        self.assertEqual((i["N_kept_words"], i["M_kept_tokens"], i["L_dysfluency_candidates"]), (10, 11, 1))
        self.assertEqual(i["C_confidence"], 0.85)
        self.assertEqual(i["CWR_clear_word_ratio"], 0.9)
        self.assertEqual(result["articulation_score"], 87.5)
        self.assertEqual(result["articulation_level"], "good")
        self.assertEqual(result["filler_count"], 1)
        self.assertEqual(result["reliability"], "normal")

    def test_worked_example_6_2_method_a(self):
        # N = 9, S = 1 (red -> wed), D = 0, I = 1 (repeated "sat") -> 100 x (1 - 2/9) = 77.78, fair
        result = score_component1(READING)
        self.assertEqual(result["method"], "A_word_accuracy")
        i = result["inputs"]
        self.assertEqual((i["N_reference_words"], i["S"], i["D"], i["I"]), (9, 1, 0, 1))
        self.assertEqual(result["articulation_score"], 77.78)
        self.assertEqual(result["articulation_level"], "fair")

    def test_fillers_counted_by_component1_wer_but_not_ours(self):
        # Component 1 WER on the full transcript counts "um" as an insertion: S=1, D=0, I=2
        c1_words = normalise_words(READING["transcript"])
        self.assertEqual(word_errors(normalise_words(READING["reference_text"]), c1_words),
                         {"substitutions": 1, "deletions": 0, "insertions": 2, "correct": 8})

    def test_reference_text_ignored_unless_reading(self):
        c1 = {**READING, "task_type": "picture"}
        self.assertEqual(score_component1(c1)["method"], "B_confidence_clear_word_ratio")

    def test_word_accuracy_clipped_at_zero(self):
        c1 = {**READING, "reference_text": "cat"}
        self.assertEqual(score_component1(c1)["articulation_score"], 0.0)

    def test_r1_threshold_from_component1(self):
        c1 = copy.deepcopy(PICTURE)
        for seg in c1["word_segments"]:
            del seg["is_dysfluency_candidate"]
        c1["dysfluency_threshold"] = 0.92  # "boy" 0.90, "climbing" 0.50, "on" 0.91, "boy" 0.88
        self.assertEqual(score_component1(c1)["inputs"]["L_dysfluency_candidates"], 4)

    def test_fallback_overall_confidence_flagged(self):
        c1 = copy.deepcopy(PICTURE)
        for seg in c1["word_segments"]:
            del seg["tokens"]
        result = score_component1(c1)
        self.assertEqual(result["inputs"]["C_confidence"], 0.8125)
        self.assertEqual(result["inputs"]["C_source"], "overall_confidence_percent")
        self.assertIn("confidence_includes_fillers", result["reliability_flags"])
        self.assertEqual(result["reliability"], "reduced")

    def test_confidence_missing_uses_cwr_only(self):
        c1 = copy.deepcopy(PICTURE)
        for seg in c1["word_segments"]:
            del seg["tokens"]
        del c1["overall_confidence_percent"]
        result = score_component1(c1)
        self.assertEqual(result["articulation_score"], 90.0)
        self.assertIn("confidence_missing", result["reliability_flags"])

    def test_reliability_flags(self):
        c1 = copy.deepcopy(PICTURE)
        c1["acoustic_features"]["snr_db"] = 8
        c1["schema_version"] = "2.0.0"
        c1["word_segments"] = c1["word_segments"][:3]
        flags = score_component1(c1)["reliability_flags"]
        self.assertEqual(flags, ["too_few_words", "noisy_recording", "schema_mismatch"])

    def test_only_fillers_is_insufficient(self):
        c1 = {**PICTURE, "word_segments": [{"word": "Um,"}, {"word": "uh"}]}
        result = score_component1(c1)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["filler_count"], 2)

    def test_invalid_probability_rejected(self):
        c1 = copy.deepcopy(PICTURE)
        c1["word_segments"][0]["tokens"][0]["probability"] = 95
        with self.assertRaises(ValueError):
            score_component1(c1)


class Component1PipelineTests(unittest.TestCase):
    def test_payload_passes_ids_through(self):
        result = process_component1_output(PICTURE)
        self.assertTrue(result["ready_for_component3"])
        payload = result["component3_input"]
        for key in ("analysis_id", "session_id", "patient_id", "age_bracket", "task_type"):
            self.assertEqual(payload[key], PICTURE[key])
        self.assertEqual(payload["articulation_score"], 87.5)
        self.assertEqual(payload["filler_count"], 1)

    def test_no_words_not_ready(self):
        result = process_component1_output({**PICTURE, "word_segments": []})
        self.assertFalse(result["ready_for_component3"])
        self.assertEqual(result["score_status"], "insufficient_data")

    def test_gloss_marks_dysfluency_candidates_unscored(self):
        words, unscored = gloss_from_component1(PICTURE)
        self.assertEqual([words[i] for i in sorted(unscored)], ["um", "climbing"])

    def test_audio_pcc_replaces_json_score(self):
        result = process_component1_output(PICTURE, fake_audio_analysis(PRODUCED))
        payload = result["component3_input"]
        self.assertEqual(payload["method"], "pcc_r")
        # 10 scored consonants (ð b z ð b z n ð t ɹ), one error (/r/ -> [w] in "tree")
        self.assertEqual(payload["articulation_score"], 90.0)
        self.assertEqual(result["articulation_score"]["articulation_score"], 87.5)


class Component3ClientTests(unittest.TestCase):
    def test_not_configured(self):
        with mock.patch.dict(os.environ, {"SPEAKFREE_COMPONENT3_URL": ""}):
            self.assertEqual(send_to_component3({})["status"], "not_configured")

    def test_sent(self):
        with mock.patch.dict(os.environ, {"SPEAKFREE_COMPONENT3_URL": "http://c3.test/in"}), \
                mock.patch("services.component3_client.requests.post") as post:
            post.return_value.status_code = 200
            delivery = send_to_component3({"articulation_score": 87.5})
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"], {"articulation_score": 87.5})
        self.assertEqual(delivery["status"], "sent")

    def test_failure_reported_not_raised(self):
        import requests
        with mock.patch.dict(os.environ, {"SPEAKFREE_COMPONENT3_URL": "http://c3.test/in"}), \
                mock.patch("services.component3_client.requests.post",
                           side_effect=requests.ConnectionError("refused")):
            self.assertEqual(send_to_component3({})["status"], "failed")


if __name__ == "__main__":
    unittest.main()
