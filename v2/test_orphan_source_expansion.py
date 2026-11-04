#!/usr/bin/env python3
"""One offline grouped safety suite for source references used only in orphan repair."""
import json
from pathlib import Path
import tempfile
import unittest
from orphan_source_expansion import safe_reference_url, reviewed_source_references


class OrphanSourceExpansionTests(unittest.TestCase):
    def test_trusted_hosts_and_no_secrets_or_private_paths(self):
        accepted = [
            "https://raw.githubusercontent.com/public/tv/main/tr.m3u",
            "https://gist.githubusercontent.com/public/abc/raw/az.m3u8",
            "https://codeberg.org/public/tv/raw/branch/main/tv.m3u",
            "https://gitlab.com/api/v4/projects/42/repository/files/tr.m3u/raw?ref=main",
        ]
        for url in accepted:
            self.assertTrue(safe_reference_url(url), url)
        for url in [
            "http://raw.githubusercontent.com/public/tv/tr.m3u",
            "https://127.0.0.1/tr.m3u",
            "https://raw.githubusercontent.com/private/tr.m3u?token=secret",
            "https://codeberg.org/public/../private/tr.m3u",
            "https://example.net/tr.m3u",
            "https://gitlab.com/api/v4/projects/42/repository/files/tr.m3u/raw?ref=main&token=bad",
        ]:
            self.assertFalse(safe_reference_url(url), url)

    def test_deduplicated_real_report_references_no_playback_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "github.json", Path(temp) / "forge.json"
            shared = "https://raw.githubusercontent.com/public/tv/main/tr.m3u"
            a.write_text(json.dumps({"sources": [
                {"url": shared, "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "entries": 3},
                {"url": shared, "status": "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED", "entries": 3},
                {"url": "https://example.net/evil.m3u", "entries": 2},
            ]}), encoding="utf-8")
            b.write_text(json.dumps({"schema": 1, "sources": [
                {"forge": "codeberg",
                 "source_url": "https://codeberg.org/public/tv/raw/branch/main/az.m3u"}
            ]}), encoding="utf-8")
            refs, stats = reviewed_source_references(set(), a, b)
            self.assertEqual(len(refs), 2)
            self.assertEqual(stats["new_source_references"], 2)
            self.assertTrue(stats["github_gist_report_checked"])
            self.assertTrue(stats["forge_report_checked"])
            self.assertFalse(stats["playback_verified"])
            self.assertFalse(stats["ibo_playlist_modified"])
            self.assertTrue(all(row["origin"] == "orphan-discovery-reference" for row in refs))

    def test_no_missing_or_invalid_report_claims_success(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "github.json", Path(temp) / "forge.json"
            a.write_text('{"sources":[]}', encoding="utf-8")
            with self.assertRaises(OSError):
                reviewed_source_references(set(), a, b)
            b.write_text('{"schema":1,"sources":{}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                reviewed_source_references(set(), a, b)


if __name__ == "__main__":
    unittest.main()
