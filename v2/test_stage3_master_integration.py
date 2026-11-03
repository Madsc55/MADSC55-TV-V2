#!/usr/bin/env python3
"""Batch master-engine regression for Stage 3 historical preservation."""
import hashlib
import unittest

from master_engine import build, archive_records, export_candidates


class Stage3MasterIntegrationTests(unittest.TestCase):
    def test_tr_and_az_scope_is_candidate_evidence_not_speech(self):
        sources = [
            ({"id": "turkish", "scope": "TR"},
             '#EXTM3U\n#EXTINF:-1,News\nhttps://fixture.example.org/tr.m3u8\n'),
            ({"id": "azeri", "scope": "AZ"},
             '#EXTM3U\n#EXTINF:-1,News\nhttps://fixture.example.org/az.m3u8\n'),
        ]
        rows, _, _ = build(sources, "#EXTM3U\n", checker=lambda x: True,
                           media_checker=lambda x: True)
        self.assertEqual({x["region_candidate"] for x in rows}, {"TR", "AZ"})
        self.assertEqual(len(export_candidates(rows)), 2)
        self.assertTrue(all(x["classification_evidence"] == "SOURCE_GEO" for x in rows))
        self.assertTrue(all(x["spoken_language_verified"] is False for x in rows))

    def test_unknown_historical_stream_is_archived_not_auto_exported(self):
        history = [{"url": "https://fixture.example.org/missing.m3u8",
                    "name": "Unidentified Channel", "source": "#60"}]
        rows, _, _ = build([], "#EXTM3U\n", history,
                           checker=lambda _: True, media_checker=lambda _: True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["region_candidate"], "UNKNOWN")
        self.assertTrue(rows[0]["media_decoded"])
        self.assertEqual(export_candidates(rows), [])
        items = archive_records(rows, history)
        self.assertEqual(items[0]["kind"], "raw_historical_evidence")
        self.assertEqual(items[0]["records"], history)
        self.assertEqual(items[1]["url"], history[0]["url"])

    def test_historical_provenance_and_missing_metadata_are_preserved(self):
        history = [{
            "url": "https://fixture.example.org/tr.m3u8", "source": "#60",
            "source_ids": ["older"], "logo": "https://fixture.example.org/old.png",
            "name": "Original Name"}]
        data = '#EXTM3U\n#EXTINF:-1,News\nhttps://fixture.example.org/tr.m3u8\n'
        rows, _, _ = build([({"id": "current", "scope": "TR"}, data)],
                           "#EXTM3U\n", history)
        self.assertEqual(len(rows), 1)
        self.assertIn("older", rows[0]["source_ids"])
        self.assertEqual(rows[0]["logo"], "https://fixture.example.org/old.png")
        self.assertEqual(rows[0]["region_candidate"], "TR")
        self.assertEqual(len(rows[0]["history"]), 1)

    def test_hash_only_and_failed_history_are_retained_even_without_urls(self):
        history = [
            {"url_sha256": hashlib.sha256(b"historic").hexdigest(), "source": "#60"},
            {"url": "http://127.0.0.1/unreachable", "status": "FAILED"},
            {"anonymous_id": "no-url"},
        ]
        rows, _, _ = build([], "#EXTM3U\n", history)
        self.assertEqual(rows, [])
        records = archive_records(rows, history)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["records"], history)

    def test_unverified_media_cannot_enter_iboplayer_exports(self):
        rows = [
            {"url": "https://fixture.example.org/tr.m3u8", "region_candidate": "TR", "media_decoded": False},
            {"url": "https://fixture.example.org/az.m3u8", "region_candidate": "AZ", "media_decoded": True},
            {"url": "https://fixture.example.org/unknown.m3u8", "region_candidate": "UNKNOWN", "media_decoded": True},
        ]
        self.assertEqual([x["url"] for x in export_candidates(rows)],
                         ["https://fixture.example.org/az.m3u8"])


if __name__ == "__main__":
    unittest.main()
