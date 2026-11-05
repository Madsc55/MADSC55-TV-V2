#!/usr/bin/env python3
"""Source-only recovery: 55/50 immutable identity and encrypted-candidate contract."""
import hashlib
import json
import unittest

from orphan_baseline_guard import load_immutable_baseline
from orphan_source_only_recheck import BASELINE, MANIFEST, verified_targets, source_only_scan


class OrphanSourceOnlyTests(unittest.TestCase):
    def test_real_10_missing_hashes_are_original_onureroz_identities(self):
        b = load_immutable_baseline(BASELINE)
        m = json.loads(MANIFEST.read_text())
        hashes = m["no_candidate_hashes"]
        self.assertEqual(len(hashes), len(set(hashes)))
        self.assertEqual(len(hashes), 10)
        self.assertTrue(set(hashes) <= set(b["sources"]["onureroz-turk-all"]) |
                        set(b["sources"]["onureroz-turk-karma"]))
        with self.assertRaises(ValueError):
            verified_targets(b, m, {"onureroz-turk-all": "",
                                    "onureroz-turk-karma": ""})

    def test_only_hash_verified_candidate_can_be_sealed_no_av_claim(self):
        targets = []
        for i in range(10):
            item = "#EXTINF:-1,Channel%d" % i
            targets.append({"extinf": item,
                            "extinf_sha256": hashlib.sha256(item.encode()).hexdigest()})
        url = "https://example.org/stream.m3u8"
        digest = hashlib.sha256(url.encode()).hexdigest()
        def lookup(rows, known):
            return [{"id": "pinned", "origin": "orphan-discovery-reference",
                     "url": "https://raw.githubusercontent.com/a/b/" + "a"*40 + "/tr.m3u8"}], {
                "queries_attempted": 20, "unavailable_or_failed_queries": 0,
                "incomplete_search_queries": 0, "truncated_queries_or_references": 0}
        def matcher(rows, refs):
            return {targets[0]["extinf_sha256"]: {digest: {
                "url": url, "proof_rules": ["EXACT_ORIGINAL_EXTINF"],
                "proof_existing_source_ids": ["pinned"]}}}, {
                "source_documents_unavailable_count": 0}
        report, rows = source_only_scan(targets, search=lookup, match=matcher)
        self.assertEqual(report["exact_identity_matches"], 1)
        self.assertEqual(report["still_without_exact_candidate"], 9)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], url)
        self.assertNotIn(url, json.dumps(report))
        self.assertFalse(report["video_audio_verified"])
        self.assertFalse(report["protected_playlist_modified"])

    def test_query_failure_buckets_are_public_only_and_do_not_approve_av(self):
        targets = []
        for i in range(10):
            meta = "#EXTINF:-1 tvg-id=\\\"Protected%02d.tr\\\",Example" % i
            targets.append({"extinf": meta,
                            "extinf_sha256": hashlib.sha256(meta.encode()).hexdigest()})
        def lookup(rows, known):
            return [], {"queries_attempted": 16, "unavailable_or_failed_queries": 11,
                        "anonymous_error_categories": {"HTTP_403": 7, "HTTP_422": 4},
                        "incomplete_search_queries": 0,
                        "truncated_queries_or_references": 0}
        def matcher(rows, refs):
            return {}, {"source_documents_unavailable_count": 0}
        report, sealed = source_only_scan(targets, search=lookup, match=matcher)
        self.assertEqual(report["anonymous_code_search_error_categories"],
                         {"HTTP_403": 7, "HTTP_422": 4})
        self.assertFalse(report["discovery_complete"])
        self.assertEqual(report["encrypted_candidate_rows"], 0)
        self.assertEqual(sealed, [])
        self.assertFalse(report["video_audio_verified"])
        self.assertNotIn("https://", str(report))

    def test_rate_limit_deferred_queries_are_never_called_complete(self):
        targets = []
        for i in range(10):
            meta = "#EXTINF:-1,Deferred%d" % i
            targets.append({"extinf": meta,
                            "extinf_sha256": hashlib.sha256(meta.encode()).hexdigest()})
        def lookup(rows, known):
            return [], {"queries_attempted": 1,
                        "queries_deferred_due_rate_limit": 9,
                        "unavailable_or_failed_queries": 0,
                        "incomplete_search_queries": 0,
                        "truncated_queries_or_references": 0}
        def matcher(rows, refs):
            return {}, {"source_documents_unavailable_count": 0}
        report, candidates = source_only_scan(targets, search=lookup, match=matcher)
        self.assertEqual(report["queries_deferred_due_rate_limit"], 9)
        self.assertFalse(report["discovery_complete"])
        self.assertEqual(report["still_without_exact_candidate"], 10)
        self.assertEqual(candidates, [])
        self.assertFalse(report["video_audio_verified"])

    def test_untrusted_candidate_sha_and_extra_identity_fail_closed(self):
        targets = []
        for i in range(10):
            m = "#EXTINF:-1,X%d" % i
            targets.append({"extinf": m, "extinf_sha256": hashlib.sha256(m.encode()).hexdigest()})
        def lookup(rows, known):
            return [], {"queries_attempted": 0, "unavailable_or_failed_queries": 0,
                        "incomplete_search_queries": 0, "truncated_queries_or_references": 0}
        def matcher(rows, refs):
            return {targets[0]["extinf_sha256"]: {"0"*64: {
                "url": "https://public.example.org/a.m3u8", "proof_rules": [],
                "proof_existing_source_ids": []}}}, {"source_documents_unavailable_count": 0}
        with self.assertRaises(ValueError):
            source_only_scan(targets, search=lookup, match=matcher)


if __name__ == "__main__":
    unittest.main()
