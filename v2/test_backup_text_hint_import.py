import unittest
from v2.backup_text_hint_import import import_text_hints, POLICY

KEY = "a" * 64

class TextHintImportTests(unittest.TestCase):
    def test_both_hints_without_approval(self):
        rows = import_text_hints({"policy": POLICY, "results": [{
            "url_sha256": KEY, "ocr_hint": True, "subtitle_hint": True,
            "language_evidence_verified": True, "review_approved": True,
            "raw_text": "SECRET"}]}, {KEY})
        self.assertTrue(rows[KEY]["ocr_turkish_hint"])
        self.assertTrue(rows[KEY]["subtitle_turkish_hint"])
        self.assertFalse(rows[KEY]["language_evidence_verified"])
        self.assertFalse(rows[KEY]["review_approved"])
        self.assertNotIn("raw_text", rows[KEY])

    def test_wrong_policy_rejected(self):
        with self.assertRaises(ValueError):
            import_text_hints({"policy": "AUTO_APPROVED", "results": []})

    def test_unknown_channel_rejected(self):
        with self.assertRaises(ValueError):
            import_text_hints({"policy": POLICY, "results": [{"url_sha256": KEY}]}, {"b" * 64})

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            import_text_hints({"policy": POLICY, "results": [
                {"url_sha256": KEY}, {"url_sha256": KEY}]})

    def test_non_boolean_hint_rejected_as_proof(self):
        rows = import_text_hints({"policy": POLICY, "results": [
            {"url_sha256": KEY, "ocr_hint": "true", "subtitle_hint": 1}]})
        self.assertFalse(rows[KEY]["ocr_turkish_hint"])
        self.assertFalse(rows[KEY]["subtitle_turkish_hint"])

    def test_excessive_batch_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            import_text_hints({"policy": POLICY, "results": [
                {"url_sha256": format(i, "064x")} for i in range(17)]})

if __name__ == "__main__":
    unittest.main()
