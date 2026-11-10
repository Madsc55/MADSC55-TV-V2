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

    def test_ambiguous_or_fragmented_urls_are_rejected(self):
        for url in ("https://example.org/live.m3u8#fragment",
                    "https://example.org/live.m3u8\n",
                    "https://example.org/live.m3u8\t",
                    "https://-bad.example.org/live.m3u8",
                    "https://bad-.example.org/live.m3u8"):
            with self.subTest(url=repr(url)):
                self.assertFalse(validate_url(url))

    def test_malformed_dns_labels_are_rejected(self):
        for host in ("foo..example.org", "foo.-bar.example.org",
                     "foo.bar-.example.org", "a" * 64 + ".example.org",
                     "a" * 250 + ".org", "example", "0x"):
            with self.subTest(host=host):
                self.assertFalse(validate_url(f"https://{host}/live.m3u8"))
        self.assertTrue(validate_url("https://cdn.example.org/live.m3u8"))
        # A globally routable numeric IPv4 address is not a malformed DNS label.
        self.assertTrue(validate_url("https://1.2.3.4/live.m3u8"))

    def test_malformed_ipv6_authority_is_rejected(self):
        self.assertFalse(validate_url("https://[broken/a.m3u8"))
        self.assertFalse(validate_url("https://[::1/a.m3u8"))

    def test_public_and_private_ip_literal_recovery_boundary(self):
        # Real public IP sources remain candidates; local/private literals cannot
        # be smuggled into the historical AV probing queue.
        for url in ("https://1.2.3.4/live.m3u8",
                    "https://[2606:4700:4700::1111]/live.m3u8"):
            with self.subTest(public=url):
                self.assertTrue(validate_url(url))
        for url in ("http://192.168.1.1/live.m3u8",
                    "http://169.254.169.254/latest/meta-data/",
                    "https://[::1]/live.m3u8",
                    "https://[fc00::1]/live.m3u8",
                    "https://[::ffff:127.0.0.1]/live.m3u8"):
            with self.subTest(private=url):
                self.assertFalse(validate_url(url))
        recovered, report = recover(
            [{"url": "https://1.2.3.4/live.m3u8", "source_id": "historic"},
             {"url": "http://169.254.169.254/latest/meta-data/"}], [])
        self.assertEqual(len(recovered), 1)
        self.assertEqual(report["historical_missing_real_url"], 1)
        self.assertIs(recovered[0]["av_verified"], False)

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

    def test_duplicate_historical_sources_are_all_preserved(self):
        old = [
            {"url": "https://example.org/live.m3u8", "source": "#60", "name": "original"},
            {"url": "https://example.org/live.m3u8", "source_id": "#61"},
            {"url": "https://example.org/live.m3u8", "source_ids": ["#62", "#60"]},
        ]
        recovered, report = recover(old, [])
        self.assertEqual(report["recoverable_real_urls"], 1)
        self.assertEqual(report["duplicate_historical_urls"], 2)
        self.assertEqual(report["additional_source_associations_preserved"], 2)
        self.assertEqual(recovered[0]["source_ids"], ["#60", "#61", "#62"])
        self.assertEqual(recovered[0]["name"], "original")
        self.assertEqual(recovered[0]["status"], "HISTORICAL_NOT_REVERIFIED")

    def test_non_object_historical_records_fail_closed(self):
        for bad in (None, "broken", ["not", "an", "object"], 123):
            with self.subTest(record=bad):
                with self.assertRaisesRegex(ValueError, "requires object records"):
                    recover([{"url": "https://example.org/live.m3u8"}, bad], [])
                with self.assertRaisesRegex(ValueError, "requires object records"):
                    recover([], [bad])

    def test_no_fabricated_urls(self):
        recovered, report = recover([{"anonymous_id": "4955"}], [])
        self.assertEqual(recovered, [])
        self.assertEqual(report["recoverable_real_urls"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
