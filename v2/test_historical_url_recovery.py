#!/usr/bin/env python3
"""No-network historical recovery contract tests."""
import unittest
from historical_url_recovery import recover, validate_url

class HistoricalRecoveryTests(unittest.TestCase):
    def test_preserves_real_urls_and_metadata(self):
        old = [{"url": "https://example.org/a.m3u8", "name": "A", "source": "#60"},
               {"url": "https://example.org/a.m3u8", "name": "duplicate"},
               {"url": "https://example.org/current.m3u8"},
               {"anonymous_id": "no-url"},
               {"url": "javascript:alert(1)"}]
        new = [{"url": "https://example.org/current.m3u8"}]
        recovered, report = recover(old, new)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["name"], "A")
        self.assertEqual(recovered[0]["source"], "#60")
        self.assertEqual(recovered[0]["recovery_status"], "HISTORICAL_NOT_REVERIFIED")
        self.assertEqual(report["historical_missing_real_url"], 2)
        self.assertFalse(report["device_verified"])

    def test_rejects_private_and_credentialed_urls(self):
        for url in ("http://127.0.0.1/a.m3u8", "http://10.0.0.1/a.m3u8",
                    "https://localhost/a.m3u8", "https://user:pass@example.org/a.m3u8",
                    "https://@example.org/a.m3u8", "https://:pass@example.org/a.m3u8"):
            self.assertFalse(validate_url(url), url)

    def test_rejects_alternate_loopback_host_notations(self):
        for host in ("127.1", "2130706433", "0177.0.0.1", "0x7f000001",
                     "foo.localhost", "localhost."):
            self.assertFalse(validate_url(f"https://{host}/live.m3u8"), host)
        self.assertTrue(validate_url("https://example.org/live.m3u8"))

    def test_malformed_ipv6_authority_is_rejected(self):
        self.assertFalse(validate_url("https://[broken/a.m3u8"))
        self.assertFalse(validate_url("https://[::1/a.m3u8"))

    def test_historical_duplicates_are_not_reintroduced(self):
        old = [{"url": "https://example.org/a.m3u8", "name": "original"},
               {"url": "https://example.org/a.m3u8", "name": "duplicate"},
               {"url": "https://example.org/b.m3u8", "name": "B"}]
        recovered, report = recover(old, [{"url": "https://example.org/b.m3u8"}])
        self.assertEqual([row["url"] for row in recovered], ["https://example.org/a.m3u8"])
        self.assertEqual(recovered[0]["name"], "original")
        self.assertEqual(report["recoverable_real_urls"], 1)

    def test_historical_success_flags_do_not_become_new_av_proof(self):
        flags = ("av_verified", "device_verified", "video_verified",
                 "audio_verified", "playback_verified", "ibo_device_verified")
        row = {"url": "https://example.org/old-live.m3u8", "source": "#60"}
        row.update({flag: True for flag in flags})
        recovered, report = recover([row], [])
        self.assertEqual(len(recovered), 1)
        for flag in flags:
            self.assertIs(recovered[0][flag], False, flag)
        self.assertTrue(all(row[flag] is True for flag in flags))
        self.assertEqual(recovered[0]["source"], "#60")
        self.assertEqual(recovered[0]["recovery_status"], "HISTORICAL_NOT_REVERIFIED")
        self.assertIs(report["device_verified"], False)

    def test_old_decoded_status_is_quarantined_but_source_is_preserved(self):
        old = {"url": "https://example.org/historical.m3u8",
               "status": "VIDEO_AUDIO_DECODED", "source": "#60",
               "av_verified": True}
        recovered, _ = recover([old], [])
        self.assertEqual(recovered[0]["status"], "HISTORICAL_NOT_REVERIFIED")
        self.assertEqual(recovered[0]["historical_status"], "VIDEO_AUDIO_DECODED")
        self.assertEqual(recovered[0]["source"], "#60")
        self.assertIs(recovered[0]["av_verified"], False)
        self.assertEqual(old["status"], "VIDEO_AUDIO_DECODED")

    def test_no_fabricated_urls(self):
        recovered, report = recover([{"anonymous_id": "4955"}], [])
        self.assertEqual(recovered, [])
        self.assertEqual(report["recoverable_real_urls"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
