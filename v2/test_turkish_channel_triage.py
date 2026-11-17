import unittest
from v2.turkish_channel_triage import classify_channel as classify

class TurkishChannelTriageTests(unittest.TestCase):
    def test_turkish_speech_without_turkish_name_abroad(self):
        r = classify("Global Haber", origin_country="DE", spoken_language="tr")
        self.assertEqual(r["category"], "TURKISH_SPOKEN_REVIEW")
        self.assertFalse(r["turkish_origin_hint"])
        self.assertTrue(r["turkish_spoken_hint"])
    def test_turkish_origin_english_speech(self):
        r = classify("TRT World", origin_country="TR", spoken_language="en")
        self.assertEqual(r["category"], "TURKEY_OR_NORTHERN_CYPRUS_ORIGIN_REVIEW")
        self.assertFalse(r["turkish_spoken_hint"])
    def test_foreign_channel_turkish_subtitle(self):
        r = classify("Global Cinema", origin_country="US", spoken_language="en",
                     subtitle_language="tr-TR")
        self.assertEqual(r["category"], "TURKISH_SUBTITLED_REVIEW")
        self.assertFalse(r["turkish_spoken_hint"])
    def test_name_only_is_not_proof(self):
        r = classify("TURK TV")
        self.assertEqual(r["category"], "TURKISH_NAME_REVIEW")
        self.assertFalse(r["language_evidence_verified"])
    def test_turkic_country_and_language(self):
        r = classify("Baku News", origin_country="AZ", spoken_language="az")
        self.assertEqual(r["category"], "OTHER_TURKIC_SPOKEN_REVIEW")
    def test_unchecked_media_not_working(self):
        r = classify("Haber Global", video_decoded=True, audio_decoded=True)
        self.assertFalse(r["av_decoded_in_supplied_check"])
        self.assertFalse(r["working_channel_verified"])
    def test_supplied_av_not_device_approval(self):
        r = classify("Haber Global", stream_checked=True,
                     video_decoded=True, audio_decoded=True)
        self.assertTrue(r["av_decoded_in_supplied_check"])
        self.assertFalse(r["working_channel_verified"])
        self.assertFalse(r["review_approved"])
        self.assertFalse(r["playlist_modified"])
    def test_turkish_script_title_without_keyword(self):
        r = classify("Güneş Haber")
        self.assertEqual(r["category"], "TURKISH_NAME_REVIEW")
        self.assertFalse(r["turkish_spoken_hint"])
        self.assertFalse(r["review_approved"])
    def test_reject_invalid_inputs(self):
        with self.assertRaises(ValueError):
            classify("")
        with self.assertRaises(ValueError):
            classify("Channel", stream_checked=1)

if __name__ == "__main__":
    unittest.main()
