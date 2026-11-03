#!/usr/bin/env python3
"""Grouped offline tests for dated Dearbulut health historical URL identities."""
import hashlib
import json
import unittest
from unittest.mock import patch
from stage3_dearbulut_health_recovery import audit_health


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DearbulutHistoricalHealthTests(unittest.TestCase):
    def test_health_rows_match_exact_urls_with_no_public_stream_values(self):
        url = "https://fixture.example.org/live.m3u8?token=EXACT"
        wrong = "https://fixture.example.org/live.m3u8?token=WRONG"
        history = [{"url_sha256": sha(url)}] + [
            {"url_sha256": sha("missing-%d" % i)} for i in range(4954)
        ]
        data = json.dumps([{"url": url}, {"url": wrong}]).encode()
        with patch("stage3_dearbulut_health_recovery._read",
                   return_value=data):
            result = audit_health(history)
        self.assertEqual(result["recovered_unique_url_hashes"], 1)
        self.assertEqual(result["still_unmatched_in_health"], 4954)
        self.assertEqual(result["matched_hashes"], [sha(url)])
        self.assertNotIn(url, str(result))
        self.assertFalse(result["device_verified"])
        self.assertTrue(all(x["exact_url_hash_matches"] == 1
                            for x in result["source_audit"]))

    def test_unavailable_original_health_does_not_erase_history(self):
        history = [{"url_sha256": sha("missing-%d" % i)} for i in range(4955)]
        with patch("stage3_dearbulut_health_recovery._read",
                   side_effect=ValueError("missing evidence")):
            result = audit_health(history)
        self.assertEqual(result["recovered_unique_url_hashes"], 0)
        self.assertEqual(result["still_unmatched_in_health"], 4955)
        self.assertTrue(all(x["status"] == "HISTORICAL_HEALTH_UNAVAILABLE"
                            for x in result["source_audit"]))


if __name__ == "__main__":
    unittest.main()
