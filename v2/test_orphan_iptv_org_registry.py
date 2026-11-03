#!/usr/bin/env python3
"""Grouped no-network regression tests for public registry orphan rescue."""
import json
import unittest
import hashlib
from orphan_iptv_org_registry import (
    find_exact_orphan_streams, CHANNELS_ENDPOINT, STREAMS_ENDPOINT
)

class OrphanIptvOrgRegistryTests(unittest.TestCase):
    def setUp(self):
        self.meta = '#EXTINF:-1 tvg-id="A.tr" tvg-logo="other.png",Channel A'
        self.row = {"extinf": self.meta,
                    "extinf_sha256": hashlib.sha256(self.meta.encode()).hexdigest()}
        self.channels = [{"id": "A.tr", "name": "Channel A", "alt_names": ["Kanal A"],
                          "is_nsfw": False, "closed": None}]
        self.streams = [{"channel": "A.tr", "title": "Edited Stream Title",
                         "url": "https://public.example.org/a.m3u8",
                         "referrer": None, "user_agent": None}]
        self.calls = []
    def reader(self, url):
        self.calls.append(url)
        return json.dumps(self.channels if url == CHANNELS_ENDPOINT else
                          self.streams).encode()
    def check(self, orphans=None):
        return find_exact_orphan_streams(self.row and [self.row]
                                         if orphans is None else orphans,
                                         fetcher=self.reader)

    def test_exact_id_and_exact_registry_name_match_even_when_stream_title_differs(self):
        found, stats = self.check()
        self.assertEqual(stats["matched_orphan_metadata_identities"], 1)
        self.assertEqual(stats["unique_exact_registry_urls"], 1)
        self.assertEqual(len(found[self.row["extinf_sha256"]]), 1)
        self.assertEqual(self.calls, [CHANNELS_ENDPOINT, STREAMS_ENDPOINT])
    def test_same_name_different_id_never_match(self):
        self.channels[0]["id"] = "Other.tr"
        found, stats = self.check()
        self.assertEqual(found, {})
    def test_same_id_different_name_never_match(self):
        self.channels[0]["name"] = "Other Channel"
        self.channels[0]["alt_names"] = []
        found, stats = self.check()
        self.assertEqual(found, {})
    def test_stream_title_alone_not_identity(self):
        self.channels[0]["name"] = "Not Channel A"
        self.channels[0]["alt_names"] = []
        self.streams[0]["title"] = "Channel A"
        found, _ = self.check()
        self.assertEqual(found, {})
    def test_registered_exact_alt_name_is_allowed(self):
        self.channels[0]["name"] = "Other Channel"
        self.channels[0]["alt_names"] = ["Channel A"]
        found, _ = self.check()
        self.assertEqual(len(found), 1)
    def test_http_referrer_and_user_agent_require_separate_evidence(self):
        self.streams[0]["referrer"] = "https://example.org/"
        found, stats = self.check()
        self.assertEqual(found, {})
        self.assertEqual(stats["streams_requiring_headers_skipped"], 1)
    def test_closed_and_nsfw_not_recovered(self):
        self.channels[0]["closed"] = "2022-01-01"
        found, _ = self.check()
        self.assertEqual(found, {})
        self.channels[0]["closed"] = None
        self.channels[0]["is_nsfw"] = True
        found, _ = self.check()
        self.assertEqual(found, {})
    def test_nonpublic_candidate_skipped(self):
        self.streams[0]["url"] = "http://127.0.0.1/secret"
        found, stats = self.check()
        self.assertEqual(found, {})
        self.assertEqual(stats["invalid_or_nonpublic_stream_urls_skipped"], 1)
    def test_invalid_json_does_not_fabricate_recovery(self):
        found, stats = find_exact_orphan_streams([self.row], fetcher=lambda _: b"not json")
        self.assertEqual(found, {})
        self.assertEqual(stats["status"], "PUBLIC_REGISTRY_UNAVAILABLE")
    def test_no_tvg_id_does_not_request_network(self):
        entry = dict(self.row, extinf="#EXTINF:-1,Channel A")
        found, stats = self.check([entry])
        self.assertEqual(found, {})
        self.assertEqual(self.calls, [])
        self.assertEqual(stats["status"], "NO_EPG_AND_NAME_IDENTITIES_TO_MATCH")
    def test_invalid_large_registry_fails_closed(self):
        found, stats = find_exact_orphan_streams(
            [self.row], fetcher=lambda _: b"[" + (b"x"*32000001) + b"]")
        self.assertEqual(found, {})
        self.assertEqual(stats["status"], "PUBLIC_REGISTRY_UNAVAILABLE")
    def test_duplicate_streams_deduplicated(self):
        self.streams.append(dict(self.streams[0]))
        found, stats = self.check()
        self.assertEqual(len(found[self.row["extinf_sha256"]]), 1)
        self.assertEqual(stats["unique_exact_registry_urls"], 1)
    def test_plaintext_only_in_private_caller_memory_not_stats(self):
        found, stats = self.check()
        self.assertNotIn("public.example.org", json.dumps(stats))
        self.assertIn("public.example.org", str(found))
    def test_one_time_live_recovery_remains_single_push_read_only(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/v2-actions-trigger-protection.yml").read_text(
                      encoding="utf-8")
        block=workflow.split("\n  orphan-46-live-recovery:",1)
        self.assertEqual(len(block),2)
        self.assertIn("github.event.head_commit.message == 'feat(v2): run exact 46 orphan AV rescue with pinned public registry'",block[1])
        self.assertIn("    needs: grouped-protection-check",block[1])
        self.assertIn("    permissions:\n      contents: read",block[1])
        self.assertIn("--include-public-registry",block[1])
        self.assertIn("RECOVERY_INCOMPLETE_REAL_VIDEO_AUDIO_REQUIRED",block[1])
        self.assertNotIn("git push ",block[1])
        self.assertNotIn("git commit ",block[1])

if __name__ == "__main__":
    unittest.main()
