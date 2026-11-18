import unittest
from v2.turkish_webvtt_evidence import extract_webvtt

class WebVTTEvidenceTests(unittest.TestCase):
    def test_turkish_header_only_creates_review(self):
        r = extract_webvtt("TV", "WEBVTT\\nLanguage: tr\\n\\n00:00:00.000 --> 00:00:01.000\\nMerhaba")
        self.assertEqual(r["category"], "TURKISH_SUBTITLED_REVIEW")
        self.assertFalse(r["turkish_spoken_hint"])
        self.assertFalse(r["review_approved"])
    def test_cue_text_cannot_forge_header(self):
        with self.assertRaises(ValueError):
            extract_webvtt("TV", "WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nLanguage: tr")
    def test_missing_language_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_webvtt("TV", "WEBVTT\\n\\nHello")
    def test_duplicate_language_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_webvtt("TV", "WEBVTT\\nLanguage: tr\\nLanguage: en\\n\\n")
    def test_not_webvtt(self):
        with self.assertRaises(ValueError):
            extract_webvtt("TV", "Language: tr")
    def test_oversized_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_webvtt("TV", "WEBVTT\\nLanguage: tr\\n\\n" + "a"*262144)
    def test_english_does_not_imply_turkish(self):
        r = extract_webvtt("TV", "WEBVTT\\nLanguage: en\\n\\n")
        self.assertFalse(r["turkish_subtitle_hint"])
if __name__ == "__main__":
    unittest.main()
