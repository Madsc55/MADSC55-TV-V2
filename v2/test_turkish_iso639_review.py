import unittest
from v2.turkish_channel_triage import classify_channel

class ISO639LanguageTests(unittest.TestCase):
    def test_turkish_iso639_2_speech(self):
        r = classify_channel("Foreign Channel", spoken_language="tur")
        self.assertEqual(r["category"], "TURKISH_SPOKEN_REVIEW")
        self.assertFalse(r["language_evidence_verified"])

    def test_turkish_iso639_2_subtitle(self):
        r = classify_channel("Foreign Channel", subtitle_language="tur")
        self.assertEqual(r["category"], "TURKISH_SUBTITLED_REVIEW")
        self.assertFalse(r["review_approved"])

    def test_other_turkic_three_letter_tags(self):
        for language in ("aze", "tuk"):
            with self.subTest(language=language):
                r = classify_channel("Foreign Channel", spoken_language=language)
                self.assertEqual(r["category"], "OTHER_TURKIC_SPOKEN_REVIEW")
                self.assertFalse(r["turkish_spoken_hint"])
