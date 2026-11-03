#!/usr/bin/env python3
"""Offline fixture regressions for exact historical-source SHA256 recovery."""
import hashlib
import unittest
from unittest.mock import patch
from stage3_historical_source_recovery import audit, match_feed


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Stage3HistoricalSourceTests(unittest.TestCase):
    def test_exact_hash_only_no_fuzzy_match_and_deduplicated_source(self):
        url = "https://fixture.example.org/live.m3u8?token=RIGHT"
        wrong = "https://fixture.example.org/live.m3u8?token=WRONG"
        m3u = ('#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr",Turkish fixture\n'
               + url + '\n#EXTINF:-1,Duplicate\n' + url +
               '\n#EXTINF:-1,Wrong token\n' + wrong + '\n')
        found, parsed = match_feed({sha(url)}, m3u, "github-auto-8")
        self.assertEqual(parsed, 3)
        self.assertEqual(list(found), [sha(url)])
        self.assertEqual(found[sha(url)]["url"], url)
        self.assertEqual(found[sha(url)]["source"], "github-auto-8")

    def test_4955_original_hashes_no_network_with_one_real_match_and_error(self):
        url = "https://fixture.example.org/live.m3u8?token=RIGHT"
        hashes = [sha("missing-%d" % n) for n in range(4954)]
        history = [{"url_sha256": h} for h in [sha(url)] + hashes]
        snapshot = {
            "sources": [
                {"repository": "example/public", "path": "TV-tr.m3u",
                 "entries": 2},
                {"repository": "example/missing", "path": "not-found.m3u",
                 "entries": 3},
            ]
        }
        feed = '#EXTM3U\n#EXTINF:-1,Fixture\n' + url + '\n'
        def fake_historical_commit(repo, path):
            if repo == "example/missing":
                raise ValueError("Original commit missing")
            return "a" * 40
        with patch("stage3_historical_source_recovery.historical_commit",
                   side_effect=fake_historical_commit), patch(
                       "stage3_historical_source_recovery._read",
                       return_value=feed.encode()):
            report, candidates = audit(history, snapshot)
        self.assertEqual(report["exact_original_url_hashes_recovered"], 1)
        self.assertEqual(report["original_url_hashes_still_unmatched"], 4954)
        self.assertEqual(report["source_files_unavailable"], 1)
        self.assertEqual(report["matched_hashes"], [sha(url)])
        self.assertNotIn(url, str(report))
        self.assertFalse(report["device_playback_verified"])
        self.assertEqual(candidates[0]["url"], url)

    def test_invalid_source_identity_fails_closed_without_network(self):
        history = [{"url_sha256": sha("h-%d" % n)} for n in range(4955)]
        snapshot = {"sources": [{"repository": "../private",
                                 "path": "something.m3u", "entries": 1}]}
        with self.assertRaisesRegex(ValueError, "repository"):
            audit(history, snapshot)


if __name__ == "__main__":
    unittest.main()
