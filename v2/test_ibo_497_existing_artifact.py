#!/usr/bin/env python3
"""Offline #497 source-artifact import tests; no network, scan or playlist writes."""
import hashlib
import unittest

from ibo_497_existing_artifact import build_preview
from ibo_test_result_reconcile import digest


def fixture():
    source = ('#EXTM3U\n#EXTINF:-1 group-title="FAVORITES",Outside old\nhttps://example.test/old\n' +
              ''.join('#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
                      for i in range(1, 1793))).encode()
    current = ('#EXTM3U\n#EXTINF:-1 group-title="FAVORITES",Outside changed\nhttps://example.test/new\n' +
               ''.join('#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel %d\nhttps://example.test/%d\n' % (i, i)
                       for i in range(1, 1793))).encode()
    results = []
    for i in range(1, 1793):
        url = ("https://example.test/%d" % i).encode()
        working = i <= 1107
        results.append({
            "position": i, "name": "Channel %d" % i,
            "url_sha256": hashlib.sha256(url).hexdigest(),
            "status": "AV_VERIFIED" if working else "PROBE_ERROR",
            "video": working, "audio": working,
            "decoded_av_verified": working,
            "classification": "WORKING" if working else "RECHECK_REQUIRED",
        })
    audit = {
        "schema_version": 1, "category": "YEDEKLER",
        "playlist_sha256": digest(source), "total": 1792,
        "counts": {"WORKING": 1107, "RECHECK_REQUIRED": 685},
        "timestamp_utc": "2026-11-20T00:20:09.490490+00:00",
        "results": results,
    }
    raw_report = b"synthetic test fixture"
    return source, current, audit, digest(raw_report)


class HistoricalArtifactImportTests(unittest.TestCase):
    def test_rebinds_only_when_all_yedekler_blocks_match_in_order(self):
        source, current, audit, report_sha = fixture()
        preview, manifest = build_preview(
            source, current, audit, 44640007709, report_sha)
        self.assertEqual(preview, current)
        self.assertEqual(manifest["counts"], {"verified": 1107, "uncertain": 685})
        self.assertTrue(manifest["ordered_yedekler_blocks_identical"])
        self.assertFalse(manifest["canonical_playlist_written"])
        self.assertFalse(manifest["new_scan_started"])

    def test_changed_yedekler_record_fails_closed(self):
        source, current, audit, report_sha = fixture()
        current = current.replace(b"https://example.test/1792", b"https://example.test/changed")
        with self.assertRaises(ValueError):
            build_preview(source, current, audit, 44640007709, report_sha)

    def test_changed_yedekler_order_fails_closed(self):
        source, current, audit, report_sha = fixture()
        first = b'#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel 1\nhttps://example.test/1\n'
        second = b'#EXTINF:-1 group-title="🗂️ YEDEKLER",Channel 2\nhttps://example.test/2\n'
        current = current.replace(first + second, second + first)
        with self.assertRaises(ValueError):
            build_preview(source, current, audit, 44640007709, report_sha)

    def test_wrong_run_fails_closed(self):
        source, current, audit, report_sha = fixture()
        with self.assertRaises(ValueError):
            build_preview(source, current, audit, 1, report_sha)


if __name__ == "__main__":
    unittest.main()
