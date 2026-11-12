"""Security regression tests for IBO production package eligibility."""
import unittest
from build_verified_ibo_packages import eligible

class ProductionGuard(unittest.TestCase):
    def test_fake_status_without_proof_rejected(self):
        row = {"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,
               "url":"https://example.org/live.m3u8","tvg_id":"demo"}
        self.assertFalse(eligible(row))

    def test_fake_sha_not_accepted(self):
        row = {"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,
               "url":"https://example.org/live.m3u8","tvg_id":"demo",
               "av_evidence":{"url":"https://example.org/live.m3u8","video":True,
                              "audio":True,"sha256":"fake","captured_at":"2026-11-12"}}
        self.assertFalse(eligible(row))

    def test_explicit_fixture_rejected(self):
        row = {"status":"AV_VERIFIED","video_proven":True,"audio_proven":True,
               "url":"https://example.org/live.m3u8","tvg_id":"demo",
               "fixture":True,
               "av_evidence":{"url":"https://example.org/live.m3u8","video":True,
                              "audio":True,"sha256":"a"*64,"captured_at":"2026-11-12"}}
        self.assertFalse(eligible(row))

if __name__ == "__main__":
    unittest.main()
