import unittest
from v2.turkish_asr_ocr_evidence import evaluate_observation, review_observation_batch

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
    def test_language_tag_injection_rejected(self):
        for tag in ("tr\\napproved", "tr;approved", "tr ", "tr--TR", "1", "x"*17):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                evaluate_observation("TV", {"source": "asr", "language": tag, "text": "Merhaba"})
    def test_no_transcript_text_in_output(self):
        r = evaluate_observation("TV", {"source": "asr", "language": "tr", "text": "PRIVATE_TEST_PHRASE"})
        self.assertNotIn("PRIVATE_TEST_PHRASE", str(r))
        self.assertFalse(r["observation_text_retained"])
    def test_other_turkic_language_kept_separate(self):
        r = evaluate_observation("TV", {"source": "asr", "language": "az", "text": "Salam"})
        self.assertEqual(r["category"], "OTHER_TURKIC_SPOKEN_REVIEW")
        self.assertFalse(r["review_approved"])
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

class BatchASROCRTests(unittest.TestCase):
    def test_asr_and_ocr_kept_separate(self):
        result = review_observation_batch([
            {"channel_id": "one", "name": "Foreign TV", "observation": {"source": "asr", "language": "tur", "text": "SECRET_AUDIO"}},
            {"channel_id": "two", "name": "Foreign TV", "observation": {"source": "ocr", "language": "tr", "text": "SECRET_SCREEN"}}])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["turkish_spoken_candidates"], 1)
        self.assertEqual(result["approved"], 0)
        self.assertFalse(result["playlist_modified"])
        self.assertNotIn("SECRET_AUDIO", str(result))
        self.assertNotIn("SECRET_SCREEN", str(result))
        self.assertFalse(result["results"][1]["turkish_subtitle_hint"])

    def test_duplicate_channel_rejected(self):
        item = {"channel_id": "x", "name": "TV", "observation": {"source": "asr", "language": "tr", "text": "Hi"}}
        with self.assertRaises(ValueError):
            review_observation_batch([item, item])

    def test_injected_approval_rejected(self):
        with self.assertRaises(ValueError):
            review_observation_batch([{"channel_id": "x", "name": "TV", "observation": {"source": "asr", "language": "tr", "text": "Hi"}, "approved": True}])
