#!/usr/bin/env python3
"""Offline grouped tests for V2-only Git historical exact SHA URL intersections."""
import hashlib
import unittest
from unittest.mock import patch

from stage3_git_history_forensics import candidate_blobs, iter_url_entries


class GitHistoryExactURLTests(unittest.TestCase):
    def test_m3u_preserves_original_url_bytes_for_sha256_identity(self):
        url = "https://fixture.example.org/live.m3u8?token=ABC%2F123&expires=100"
        playlist = '#EXTM3U\n#EXTINF:-1 tvg-id="TRT1.tr" group-title="TR",TRT 1\n' + url + '\n'
        rows = list(iter_url_entries("archive.m3u8", playlist.encode()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], url)
        self.assertEqual(hashlib.sha256(rows[0]["url"].encode()).hexdigest(),
                         hashlib.sha256(url.encode()).hexdigest())
        self.assertNotEqual(hashlib.sha256(url.replace("100", "101").encode()).hexdigest(),
                            hashlib.sha256(url.encode()).hexdigest())

    def test_json_stream_url_keys_only_exclude_logos_and_sources(self):
        data = b'{"streams":[{"url":"https://fixture.example.org/real.m3u8", "logo":"https://fixture.example.org/logo.png", "source_url":"https://fixture.example.org/source.m3u"}], "hls_url":"https://fixture.example.org/live.m3u8"}'
        rows = list(iter_url_entries("legacy-candidates.json", data))
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["url"] for r in rows},
                         {"https://fixture.example.org/real.m3u8",
                          "https://fixture.example.org/live.m3u8"})

    def test_hash_only_json_records_never_fabricate_stream_url(self):
        raw = b'{"candidates":[{"url_sha256":"' + b"a" * 64 + b'","source":"#60"}]}'
        self.assertEqual(list(iter_url_entries("candidates.json", raw)), [])

    def test_git_blob_audit_deduplicates_and_avoids_large_files(self):
        one, two = "1" * 40, "2" * 40
        rev = (one + " channel.m3u8\n" + one + " duplicate.m3u8\n" +
               two + " big.json\n" + "f" * 40 + " ignored.py\n").encode()
        output = (one + " blob 100\n" + two + " blob 33000000\n").encode()
        def fake_git(args, *, input_bytes=None):
            if args[0] == "rev-list":
                return rev
            if args[0] == "cat-file":
                return output
            raise AssertionError("Unexpected Git command")
        with patch("stage3_git_history_forensics.git", side_effect=fake_git):
            available, skipped = candidate_blobs()
        self.assertEqual(available, [(one, "channel.m3u8")])
        self.assertEqual(skipped, 1)


if __name__ == "__main__":
    unittest.main()
