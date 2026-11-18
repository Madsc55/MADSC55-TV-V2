import unittest
from v2.turkish_asr_ocr_evidence import evaluate_observation

class ASROCREvidenceTests(unittest.TestCase):
    def test_asr_turkish_is_review_only(self):
        r = evaluate_observation("TV", {"source": "asr", "language": "tr", "text": "Merhaba"})
        self.assertEqual(r["category"], "TURKISH_SPOKEN_REVIEW")
        self.assertFalse(r["review_approved"])
        self.assertFalse(r["language_evidence_verified"])
    def test_ocr_turkish_is_not_spoken_or_subtitle(self):
        r = evaluate_observation("TV", {"source": "ocr", "language": "tr", "text": "Haber"})
        self.assertFalse(r["turkish_spoken_hint"])
        self.assertFalse(r["turkish_subtitle_hint"])
        self.assertTrue(r["ocr_text_is_not_subtitle_or_speech"])
        self.assertEqual(r["observation_provenance"], "ocr")
        self.assertFalse(r["observed_language_is_verified"])
        self.assertFalse(r["playlist_modified"])
    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation("TV", {"source": "title", "language": "tr", "text": "TV"})
    def test_missing_text_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation("TV", {"source": "asr", "language": "tr", "text": ""})
    def test_unknown_fields_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation("TV", {"source": "asr", "language": "tr", "text": "Hi", "approved": True})
    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation("TV", {"source": "ocr", "language": "tr", "text": "x"*4097})
if __name__ == "__main__":
    unittest.main()
