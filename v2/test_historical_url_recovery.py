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

    def test_malformed_ipv6_authority_is_rejected(self):
        self.assertFalse(validate_url("https://[broken/a.m3u8"))
        self.assertFalse(validate_url("https://[::1/a.m3u8"))

    def test_no_fabricated_urls(self):
        recovered, report = recover([{"anonymous_id": "4955"}], [])
        self.assertEqual(recovered, [])
        self.assertEqual(report["recoverable_real_urls"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
