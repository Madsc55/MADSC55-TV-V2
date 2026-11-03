#!/usr/bin/env python3
"""Offline checks for exact configured-source historical identity matching."""
import hashlib
import unittest
from unittest.mock import patch
from stage3_original_configured_source_recovery import audit_configured


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class ConfiguredSourceMatchingTests(unittest.TestCase):
    def test_exact_url_hash_dedup_and_no_media_validation(self):
        url = "https://fixture.example.org/stream.m3u8"
        history = [{"url_sha256": sha(url)}] + [
            {"url_sha256": sha("missing-" + str(n))} for n in range(4954)
        ]
        playlist = ("#EXTM3U\n#EXTINF:-1,Example\n" + url + "\n").encode()
        with patch("stage3_original_configured_source_recovery._read",
                   return_value=playlist):
            result = audit_configured(history)
        self.assertEqual(result["unique_exact_url_hash_matches"], 1)
        self.assertEqual(result["unmatched_historical_hashes"], 4954)
        self.assertNotIn(url, str(result))
        self.assertFalse(result["device_verified"])

    def test_source_read_error_keeps_original_hash_count(self):
        history = [{"url_sha256": sha("missing-" + str(n))} for n in range(4955)]
        with patch("stage3_original_configured_source_recovery._read",
                   side_effect=ValueError("read failed")):
            result = audit_configured(history)
        self.assertEqual(result["unique_exact_url_hash_matches"], 0)
        self.assertEqual(result["unmatched_historical_hashes"], 4955)
        self.assertTrue(all(x["status"] == "UNAVAILABLE"
                            for x in result["source_audit"]))


if __name__ == "__main__":
    unittest.main()
