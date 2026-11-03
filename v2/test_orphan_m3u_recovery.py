#!/usr/bin/env python3
"""Grouped safety and recovery tests for the three known upstream orphan feeds."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orphan_m3u_recovery import (
    parse_exact_pairs, find_historical, find_official_alternates, evaluate, audit,
    exact_channel_identity, find_existing_exact_identity,
)


class OrphanRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.dis = "#EXTINF:-1 tvg-id=\"cnn.tr\",CNN Türk"
        self.sun = "#EXTINF:-1 tvg-id=\"k+1\",K+"
        self.onur = "#EXTINF:-1 tvg-id=\"tur.tr\",TR"
        self.a = "https://public.example.org/a.m3u8"
        self.b = "https://public.example.org/b.m3u8"

    def test_only_real_original_extinf_line_matches_archive(self):
        initial = "#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Different\n" + self.a + "\n"
        _, orphans = parse_exact_pairs(initial)
        original = "#EXTM3U\n" + self.dis + "\n" + self.a + "\n"
        matches, counts = find_historical(
            orphans, "discevisita/iptv", "tr.m3u",
            commits=lambda *a, **k: ["a"*40],
            reader=lambda url: original)
        self.assertEqual(len(matches[self.dis]), 1)
        self.assertEqual(counts["historical_files_read"], 1)

    def test_nonpublic_http_is_safely_excluded_but_not_an_orphan(self):
        from orphan_m3u_recovery import count_excluded_network_references
        content = ("#EXTM3U\n#EXTINF:-1,Private\n"
                   "http://192.168.1.10/live.m3u8\n"
                   "#EXTINF:-1,Valid\nhttps://public.example.org/good.m3u8\n")
        rows, orphan = parse_exact_pairs(content)
        self.assertEqual(len(orphan), 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(count_excluded_network_references(content), 1)

    def test_nonoriginal_source_path_cannot_be_sneaked_in(self):
        with self.assertRaisesRegex(ValueError, "outside pinned"):
            find_historical([], "somewhere/unknown", "other.m3u",
                            commits=lambda *a, **k: [])

    def test_partial_onur_official_alternates_do_not_claim_full_recovery(self):
        missing = [{"extinf": self.onur}]
        def read(url):
            if url.endswith("index.m3u"):
                return "#EXTM3U\n" + self.onur + "\n" + self.b
            return "#EXTM3U\n#EXTINF:-1,Other\n" + self.a
        evidence, status = find_official_alternates(missing, reader=read)
        self.assertEqual(len(evidence[self.onur]), 1)
        self.assertEqual(status["official_alternate_feeds_read"], 2)

    def test_no_http_url_is_inferred_from_invalid_or_missing_reference(self):
        content = ("#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Next\n" + self.a
                   + "\n#EXTINF:-1,Empty\n/relative/not-an-absolute-url\n")
        urls, missing = parse_exact_pairs(content)
        self.assertEqual(len(missing), 2)
        self.assertEqual(sum(len(s) for s in urls.values()), 1)

    def test_exact_epg_id_and_name_matching_without_fuzzy_guessing(self):
        src = '#EXTINF:-1 tvg-id="ZDF.de" tvg-logo="old.png",ZDF'
        alt = '#EXTINF:-1 tvg-id="ZDF.de" tvg-logo="new.png",ZDF'
        changed_name = '#EXTINF:-1 tvg-id="ZDF.de",ZDFneo'
        self.assertEqual(exact_channel_identity(src), exact_channel_identity(alt))
        self.assertNotEqual(exact_channel_identity(src),
                            exact_channel_identity(changed_name))
        self.assertIsNone(exact_channel_identity('#EXTINF:-1,ZDF'))

    def test_exact_existing_source_match_does_not_invent_url(self):
        src = '#EXTINF:-1 tvg-id="ZDF.de",ZDF'
        orphan = [{"extinf": src, "extinf_sha256": hashlib.sha256(src.encode()).hexdigest()}]
        catalog = [{"id": "already-known", "url": "https://feeds.example.org/world.m3u"}]
        alternate = '#EXTINF:-1 tvg-id="ZDF.de" group-title="Germany",ZDF'
        content = "#EXTM3U\n" + alternate + "\n" + self.b + "\n"
        found, stats = find_existing_exact_identity(
            orphan, catalog, reader=lambda _: content)
        digest = hashlib.sha256(self.b.encode()).hexdigest()
        self.assertEqual(found[orphan[0]["extinf_sha256"]][digest]["url"], self.b)
        self.assertEqual(stats["orphan_entries_with_exact_existing_epg_and_name"], 1)
        self.assertEqual(stats["preconfigured_sources_checked"], 1)
        self.assertEqual(stats["source_documents_unavailable_count"], 0)

    def test_probe_dedup_and_no_plaintext_in_public_report(self):
        c = {"url": self.a, "proof_commits": ["a"*40]}
        entry = {"source_id": "discevisita-tr", "extinf_sha256": "x"*64,
                 "extinf": self.dis,
                 "candidates": {hashlib.sha256(self.a.encode()).hexdigest(): c}}
        def verified(item):
            return {"url_sha256": item[0], "status": "VIDEO_STREAM_OBSERVED",
                    "video_stream": True, "audio_stream": True}
        p, rows, m = evaluate([entry, entry], probe=verified)
        self.assertEqual(len(p), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], self.a)
        self.assertIn(entry, m[p[0]["url_sha256"]])

    def test_end_to_end_three_source_batch_and_sealed_only_for_verified_av(self):
        def reader(url):
            if "discevisita/iptv/main" in url:
                return "#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Safe\n" + self.a
            if "SunshineTr/main" in url:
                return "#EXTM3U\n" + self.sun + "\n#EXTINF:-1,Safe\n" + self.b
            if "/karma-index.m3u" in url:
                return "#EXTM3U\n" + self.onur + "\n/relative.m3u8"
            if "discevisita/iptv/" in url:
                return "#EXTM3U\n" + self.dis + "\n" + self.a
            if "SunshineTr/" in url:
                return "#EXTM3U\n#EXTINF:-1,Other\n" + self.b
            if url.endswith("/index.m3u"):
                return "#EXTM3U\n" + self.onur + "\n" + self.b
            return "#EXTM3U\n"
        def probe(item):
            return {"url_sha256": item[0], "status": "VIDEO_STREAM_OBSERVED",
                    "video_stream": True, "audio_stream": item[1] == self.a}
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/"public.json"
            sealed = Path(directory)/"private.sealed"
            with patch("orphan_m3u_recovery.seal_rows") as seal:
                res = audit(report_path=report, sealed_path=sealed,
                            key_path=Path(directory)/"unused.pem", limit=1,
                            reader=reader,
                            commits=lambda *a, **k: ["a"*40], probe=probe)
                seal.assert_called_once()
                self.assertEqual(len(seal.call_args.args[0]), 1)
            public = report.read_text()
            self.assertEqual(res["orphan_entries"], 3)
            self.assertEqual(res["unique_candidates_video_audio_verified"], 1)
            self.assertEqual(res["orphan_entries_without_current_av"], 2)
            self.assertNotIn(self.a, public)
            self.assertNotIn(self.b, public)
            self.assertNotIn("CNN Türk", public)


if __name__ == "__main__":
    unittest.main()
