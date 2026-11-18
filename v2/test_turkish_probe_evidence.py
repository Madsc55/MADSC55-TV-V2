import unittest
from v2.turkish_probe_evidence import from_probe

class ProbeEvidenceTests(unittest.TestCase):
    def test_verified_av_still_not_language_or_device_proof(self):
        r = from_probe("Haber", {"status": "AV_VERIFIED", "decoded_av_verified": True})
        self.assertTrue(r["av_decoded_in_supplied_check"])
        self.assertFalse(r["language_evidence_verified"])
        self.assertFalse(r["working_channel_verified"])
        self.assertFalse(r["review_approved"])
    def test_metadata_only_does_not_claim_decoding(self):
        r = from_probe("TRT World", {"status": "AV_STREAMS_PRESENT", "decoded_av_verified": False}, origin_country="TR")
        self.assertFalse(r["av_decoded_in_supplied_check"])
        self.assertFalse(r["turkish_spoken_hint"])
    def test_missing_decode_flag_fails_closed(self):
        with self.assertRaises(ValueError):
            from_probe("TV", {"status": "AV_VERIFIED"})
    def test_contradictory_verified_status_fails_closed(self):
        with self.assertRaises(ValueError):
            from_probe("TV", {"status": "AV_VERIFIED", "decoded_av_verified": False})
    def test_contradictory_decode_flag_fails_closed(self):
        with self.assertRaises(ValueError):
            from_probe("TV", {"status": "VIDEO_ONLY", "decoded_av_verified": True})
    def test_invalid_probe_fails_closed(self):
        with self.assertRaises(ValueError):
            from_probe("TV", [])
if __name__ == "__main__":
    unittest.main()
