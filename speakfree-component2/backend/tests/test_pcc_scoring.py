import unittest

from services.pcc_scoring import score_pcc, severity_band, tokenize_words, word_intelligibility

TARGET = tokenize_words("She sells sea shells")  # ʃ i | s ɛ l z | s i | ʃ ɛ l z -> 8 consonants


class PccScoringTests(unittest.TestCase):
    def test_correct_production_scores_100(self):
        r = score_pcc(TARGET, "ʃ iː s ɛ l z s iː ʃ ɛ l z".split())
        self.assertEqual(r["counts"]["target_consonants"], 8)
        self.assertEqual(r["pcc"], 100.0)
        self.assertEqual(r["pvc"], 100.0)

    def test_interdental_lisp_is_substitution(self):
        r = score_pcc(TARGET, "ʃ iː θ ɛ l z θ iː ʃ ɛ l z".split())
        self.assertEqual(r["counts"]["substitutions"], 2)
        self.assertEqual(r["pcc"], 75.0)
        self.assertEqual(r["severity_band"], "mild-moderate")

    def test_dentalised_s_is_distortion_counted_correct_in_pcc_r(self):
        r = score_pcc(TARGET, "ʃ iː s̪ ɛ l z s̪ iː ʃ ɛ l z".split())
        self.assertEqual(r["counts"]["distortions"], 2)
        self.assertEqual(r["pcc"], 75.0)
        self.assertEqual(r["pcc_r"], 100.0)

    def test_final_consonant_deletion_is_omission(self):
        r = score_pcc(TARGET, "ʃ iː s ɛ l s iː ʃ ɛ l".split())
        self.assertEqual(r["counts"]["omissions"], 2)
        finals = [i for i in r["consonant_items"] if i["automated_result"] == "omission"]
        self.assertTrue(all(i["position"] == "final" for i in finals))

    def test_gliding_r_to_w(self):
        r = score_pcc(["tree"], "t w iː".split())
        self.assertEqual(r["counts"]["substitutions"], 1)
        self.assertEqual(r["pcc"], 50.0)

    def test_flap_is_allophone_not_error(self):
        r = score_pcc(["butter"], "b ʌ ɾ ɚ".split())
        self.assertEqual(r["pcc"], 100.0)

    def test_non_rhotic_postvocalic_r_is_dialect_variant(self):
        self.assertEqual(score_pcc(["shore"], "ʃ ɔː".split())["pcc"], 100.0)
        self.assertEqual(score_pcc(["shore"], "ʃ ɔː ɹ".split())["pcc"], 100.0)
        # prevocalic /r/ is still required
        self.assertEqual(score_pcc(["red"], "ɛ d".split())["counts"]["omissions"], 1)

    def test_additions_not_counted_as_errors(self):
        r = score_pcc(["sea"], "s t iː".split())
        self.assertEqual(r["pcc"], 100.0)
        self.assertEqual(r["counts"]["additions"], 1)

    def test_unscored_words_excluded(self):
        r = score_pcc(TARGET, "ʃ iː θ ɛ l z s iː ʃ ɛ l z".split(), unscored_word_indices={1})
        self.assertEqual(r["counts"]["target_consonants"], 5)
        self.assertEqual(r["pcc"], 100.0)

    def test_out_of_dictionary_words_excluded(self):
        r = score_pcc(["rpfp"], "ɑː ɹ p f p".split())
        self.assertEqual(r["status"], "no_scorable_consonants")
        self.assertIsNone(r["pcc"])
        self.assertEqual(r["excluded_words"], ["rpfp"])

    def test_severity_bands(self):
        self.assertEqual(severity_band(85.0), "mild")
        self.assertEqual(severity_band(84.99), "mild-moderate")
        self.assertEqual(severity_band(65.0), "mild-moderate")
        self.assertEqual(severity_band(50.0), "moderate-severe")
        self.assertEqual(severity_band(49.9), "severe")

    def test_word_intelligibility(self):
        r = word_intelligibility("the boy is climbing the tree", "the boy climbing a tree")
        self.assertEqual(r["words_correct"], 4)
        self.assertEqual(r["word_intelligibility_percent"], 66.67)


if __name__ == "__main__":
    unittest.main()
