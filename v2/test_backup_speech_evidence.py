import unittest
from v2.backup_speech_evidence import import_speech_hints

KEY = "a" * 64
POLICY = "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW"

class SpeechEvidenceTests(unittest.TestCase):
    def test_turkish_prediction_is_hint_only(self):
        report = {"policy": POLICY, "results": [{"url_sha256": KEY,
            "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "tr",
            "speech_detected": True, "language_probability": 0.99}]}
        row = import_speech_hints(report, {KEY})[KEY]
        self.assertTrue(row["spoken_turkish_hint"])
        self.assertEqual(row["language"], "UNKNOWN")
        self.assertFalse(row["language_evidence_verified"])
        self.assertFalse(row["review_approved"])

    def test_silence_cannot_prove_turkish(self):
        report = {"policy": POLICY, "results": [{"url_sha256": KEY,
            "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "tr",
            "speech_detected": False, "language_probability": 0.99}]}
        self.assertFalse(import_speech_hints(report)[KEY]["spoken_turkish_hint"])

    def test_invalid_probability_not_promoted(self):
        for value in (None, True, -0.1, 1.1, "0.9"):
            with self.subTest(value=value):
                report = {"policy": POLICY, "results": [{"url_sha256": KEY,
                    "status": "LANGUAGE_MODEL_HINT_ONLY", "detected_language": "tr",
                    "speech_detected": True, "language_probability": value}]}
                self.assertFalse(import_speech_hints(report)[KEY]["spoken_turkish_hint"])

    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):
            import_speech_hints({"policy": POLICY, "results": [{"url_sha256": KEY}]}, {"b" * 64})

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            import_speech_hints({"policy": POLICY, "results": [{"url_sha256": KEY}, {"url_sha256": KEY}]})

    def test_untrusted_policy_rejected(self):
        with self.assertRaises(ValueError):
            import_speech_hints({"policy": "AUTO_APPROVED", "results": []})

    def test_excessive_batch_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            import_speech_hints({"policy": "READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW",
                                 "results": [{"url_sha256": format(i, "064x")} for i in range(17)]})

if __name__ == "__main__":
    unittest.main()
