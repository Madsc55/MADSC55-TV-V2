import unittest
from v2.backup_text_evidence import inspect_text_observations

class TextEvidenceTests(unittest.TestCase):
    def test_ocr_turkish_letters_hint_only(self):
        r=inspect_text_observations([{"kind":"OCR","text":"Türkiye haberleri"}])
        self.assertTrue(r["observations"][0]["turkish_review_hint"])
        self.assertFalse(r["language_evidence_verified"])

    def test_subtitle_language_tag_hint_only(self):
        r=inspect_text_observations([{"kind":"SUBTITLE","text":"hello","language_tag":"tr-TR"}])
        self.assertTrue(r["observations"][0]["turkish_review_hint"])
        self.assertFalse(r["review_approved"])

    def test_empty_not_turkish(self):
        self.assertFalse(inspect_text_observations([{"kind":"OCR","text":""}])["observations"][0]["turkish_review_hint"])

    def test_reject_unbounded_text(self):
        with self.assertRaises(ValueError):
            inspect_text_observations([{"kind":"OCR","text":"x"*4097}])

    def test_reject_unknown_kind(self):
        with self.assertRaises(ValueError):
            inspect_text_observations([{"kind":"AUDIO","text":"Türkçe"}])

    def test_never_leak_raw_text(self):
        r=inspect_text_observations([{"kind":"SUBTITLE","text":"secret Türkiye"}])
        self.assertNotIn("secret",repr(r))

if __name__ == "__main__":
    unittest.main()
