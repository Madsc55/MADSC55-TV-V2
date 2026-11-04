#!/usr/bin/env python3
"""Offline grouped regression tests for targeted GitHub code-search references."""
import hashlib
import json
from urllib.parse import parse_qs, urlsplit
import unittest
from orphan_targeted_github_code import (
    query_for_metadata, pinned_public_file, targeted_source_references)


def orphan(meta):
    return {"extinf": meta,
            "extinf_sha256": hashlib.sha256(meta.encode("utf-8")).hexdigest()}


def row(path="regional.m3u", repo="public/tv", revision="a"*40):
    return {"repository": {"full_name": repo, "private": False},
            "html_url": "https://github.com/" + repo + "/blob/" + revision + "/" + path,
            "path": path, "size": 5000}


class TargetedGitHubCodeDiscoveryTests(unittest.TestCase):
    def test_pinned_public_git_sha_yields_discovery_reference_not_stream(self):
        queried = []
        def fake(uri, api=False):
            self.assertTrue(api)
            q = parse_qs(urlsplit(uri).query)["q"][0]
            queried.append(q)
            return json.dumps({"items": [row()], "incomplete_results": False}).encode()
        m = '#EXTINF:-1 tvg-id="KanalID.tr",Kanal A'
        refs, stats = targeted_source_references([orphan(m)], set(), fetcher=fake,
                                                 pause=lambda _: None)
        self.assertEqual(queried, ['"KanalID.tr" extension:m3u', '"KanalID.tr" extension:m3u8'])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["url"],
                         "https://raw.githubusercontent.com/public/tv/" + "a"*40 + "/regional.m3u")
        self.assertEqual(stats["status"], "PUBLIC_CODE_REFERENCES_ONLY")
        self.assertEqual(stats["queries_attempted"], 2)
        self.assertFalse(stats["playback_verified"])

    def test_refuses_unpinned_private_non_m3u_or_oversized_search_hits(self):
        good = row()
        invalid = [
            {**good, "html_url": good["html_url"].replace("/" + "a"*40 + "/", "/main/")},
            {**good, "repository": {"full_name": "public/tv", "private": True}},
            row(path="../secret.m3u"), row(path="playlist.json"),
            {**good, "size": 9000000},
            {**good, "repository": {"full_name": "wrong/repo", "private": False}},
        ]
        self.assertTrue(pinned_public_file(good))
        self.assertTrue(pinned_public_file(row(path="world.m3u8")))
        invalid.append({**good, "path": "wrong-file.m3u"})
        for candidate in invalid:
            self.assertIsNone(pinned_public_file(candidate))

    def test_no_sensitive_search_query_or_fabricated_identity(self):
        self.assertIsNone(query_for_metadata('#EXTINF:-1,name:has:colon'))
        self.assertIsNone(query_for_metadata('#EXTINF:-1,token=https://secret'))
        self.assertIsNone(query_for_metadata('#EXTINF:-1,TV'))
        self.assertEqual(query_for_metadata('#EXTINF:-1,Regional TV'),
                         '"Regional TV" extension:m3u')
        self.assertEqual(query_for_metadata('#EXTINF:-1,Regional TV', "m3u8"),
                         '"Regional TV" extension:m3u8')
        with self.assertRaises(ValueError):
            query_for_metadata('#EXTINF:-1,Regional TV', "ts")
        with self.assertRaisesRegex(ValueError, "exact immutable"):
            targeted_source_references(
                [{"extinf_sha256": "a"*64, "extinf": "#EXTINF:-1,Wrong"}],
                set(), fetcher=lambda *_a, **_k: b'{}')

    def test_13_deduplicated_orphans_search_both_file_types_in_one_batch(self):
        seen = []
        waits = []
        def fake(uri, api=False):
            seen.append(parse_qs(urlsplit(uri).query)["q"][0])
            return b'{"items":[],"incomplete_results":false}'
        orphans = [orphan('#EXTINF:-1 tvg-id="channel%02d.vn",Channel %d' % (i, i))
                   for i in range(13)]
        refs, stats = targeted_source_references(
            orphans + [orphans[0]], set(), fetcher=fake, pause=waits.append)
        self.assertEqual(refs, [])
        self.assertEqual(len(seen), 26)
        self.assertEqual(waits.count(8), 25)
        self.assertEqual(waits.count(65), 3)
        self.assertEqual(stats["distinct_orphan_identities_supplied"], 13)
        self.assertEqual(stats["queries_attempted"], 26)
        self.assertEqual(sum(q.endswith("extension:m3u8") for q in seen), 13)

    def test_search_rate_limit_or_invalid_json_never_claims_complete(self):
        m = '#EXTINF:-1 tvg-id="Channel.tr",Channel'
        refs, stats = targeted_source_references(
            [orphan(m)], set(),
            fetcher=lambda *a, **kw: (_ for _ in ()).throw(OSError("Rate limited")),
            pause=lambda _: None)
        self.assertEqual(refs, [])
        self.assertEqual(stats["status"], "PARTIAL_PUBLIC_CODE_SEARCH")
        self.assertEqual(stats["unavailable_or_failed_queries"], 2)

    def test_duplicate_candidate_references_remain_single(self):
        m1 = '#EXTINF:-1 tvg-id="Channel1.tr",Channel One'
        m2 = '#EXTINF:-1 tvg-id="Channel2.tr",Channel Two'
        refs, stats = targeted_source_references(
            [orphan(m1), orphan(m2)], set(),
            fetcher=lambda *a, **kw: json.dumps({"items":[row(),row()]}).encode(),
            pause=lambda _: None)
        self.assertEqual(len(refs), 1)
        self.assertGreaterEqual(stats["invalid_or_duplicate_public_references"], 1)



    def test_http_error_categories_are_anonymous_and_rate_failures_not_hidden(self):
        from urllib.error import HTTPError
        meta = '#EXTINF:-1 tvg-id="Channel.tr",Channel'
        def fake(uri, api=False):
            raise HTTPError(uri, 403, "rate-limited secret", {}, None)
        refs, report = targeted_source_references(
            [orphan(meta)], set(), fetcher=fake, pause=lambda _: None)
        self.assertEqual(refs, [])
        self.assertEqual(report["queries_attempted"], 2)
        self.assertEqual(report["unavailable_or_failed_queries"], 2)
        self.assertEqual(report["anonymous_error_categories"], {"HTTP_403": 2})
        self.assertEqual(report["status"], "PARTIAL_PUBLIC_CODE_SEARCH")
        self.assertNotIn("secret", str(report))


    def test_http_429_stops_bounded_group_and_marks_deferred_queries(self):
        from urllib.error import HTTPError
        meta = '#EXTINF:-1 tvg-id="Channel.tr",Channel'
        received = []
        def fake(uri, api=False):
            received.append(uri)
            raise HTTPError(uri, 429, "Rate limit", {}, None)
        refs, report = targeted_source_references(
            [orphan(meta)], set(), fetcher=fake, pause=lambda _: None)
        self.assertEqual(refs, [])
        self.assertEqual(len(received), 1)
        self.assertEqual(report["queries_attempted"], 1)
        self.assertEqual(report["queries_selected"], 2)
        self.assertEqual(report["queries_deferred_due_rate_limit"], 1)
        self.assertEqual(report["anonymous_error_categories"], {"HTTP_429": 1})
        self.assertEqual(report["status"], "PARTIAL_PUBLIC_CODE_SEARCH")

    def test_http_429_explicit_bounded_retry_after_can_restore_search(self):
        from urllib.error import HTTPError
        meta = '#EXTINF:-1 tvg-id="Channel.tr",Channel'
        calls, sleeps = [], []
        def fake(uri, api=False):
            calls.append(uri)
            if len(calls) == 1:
                raise HTTPError(uri, 429, "Retry after two seconds",
                                {"Retry-After": "2"}, None)
            return b'{"items":[],"incomplete_results":false}'
        refs, report = targeted_source_references(
            [orphan(meta)], set(), fetcher=fake, pause=sleeps.append)
        self.assertEqual(refs, [])
        self.assertEqual(report["queries_attempted"], 2)
        self.assertEqual(report["unavailable_or_failed_queries"], 0)
        self.assertEqual(report["queries_deferred_due_rate_limit"], 0)
        self.assertEqual(len(calls), 3)
        self.assertIn(2, sleeps)
        self.assertEqual(report["status"], "PUBLIC_CODE_REFERENCES_ONLY")


if __name__ == "__main__":
    unittest.main()
