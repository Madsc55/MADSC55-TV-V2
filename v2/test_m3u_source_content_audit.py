#!/usr/bin/env python3
"""Grouped in-memory full-source loss regressions; never uses network."""
import hashlib
import unittest

from m3u_source_content_audit import audit_contents


def digest(url):
    return hashlib.sha256(url.encode()).hexdigest()


class FullM3UCoverageTests(unittest.TestCase):
    def test_successful_header_with_zero_streams_must_not_pass(self):
        sources = [{"id": "tr", "url": "https://fixture.example/a.m3u"}]
        report = audit_contents(sources, [], lambda _: "#EXTM3U\n")
        self.assertEqual(report["source_content_review_required"], 1)
        self.assertEqual(report["source_status_counts"]["EMPTY_PLAYLIST"], 1)

    def test_current_historical_url_hash_membership_not_just_count(self):
        sources = [{"id": "tr", "url": "https://fixture.example/tr.m3u"},
                   {"id": "world", "url": "https://fixture.example/world.m3u"}]
        old = ["https://fixture.example/old.m3u8",
               "https://fixture.example/retained.m3u8"]
        def fetch(url):
            stream = old[1] if url.endswith("tr.m3u") else "https://fixture.example/new.m3u8"
            return "#EXTM3U\n#EXTINF:-1,Channel\n" + stream + "\n"
        result = audit_contents(sources, [digest(x) for x in old], fetch)
        self.assertEqual(result["union_unique_url_sha256"], 2)
        self.assertEqual(result["historical_identifiers_present_in_current_sources"], 1)
        self.assertEqual(result["historical_identifiers_absent_from_current_sources"], 1)
        self.assertEqual(result["status"], "COMPLETE_SOURCE_CONTENT_PARSED")
        self.assertEqual(result["current_streams_playback_checked"], 0)

    def test_retired_source_is_kept_in_report_but_not_fetched(self):
        sources = [{"id": "retired", "url": "https://fixture.example/deleted.m3u",
                    "enabled": False},
                   {"id": "active", "url": "https://fixture.example/active.m3u"}]
        calls = []
        def fetch(url):
            calls.append(url)
            return "#EXTM3U\n#EXTINF:-1,Channel\nhttps://fixture.example/live.m3u8"
        result = audit_contents(sources, [], fetch)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["source_results"][0]["status"], "RETIRED_IN_ORIGINAL_INVENTORY")
        self.assertEqual(result["active_sources"], 1)

    def test_parse_loss_does_not_count_as_complete(self):
        source = [{"id": "tr", "url": "https://fixture.example/one.m3u"}]
        result = audit_contents(source, [], lambda _: "#EXTM3U\n#EXTINF:-1,Missing URL\n")
        self.assertEqual(result["source_status_counts"]["INCOMPLETE_EXTINF_PAIRS"], 1)
        self.assertEqual(result["source_results"][0]["unpaired_extinf"], 1)

    def test_udp_and_rtmp_are_not_mislabelled_as_corrupt_http_streams(self):
        source = [{"id": "mixed", "url": "https://fixture.example/feed.m3u"}]
        body = ("#EXTM3U\n"
                "#EXTINF:-1,HTTP channel\nhttps://fixture.example/one.m3u8\n"
                "#EXTINF:-1,UDP channel\nudp://@239.0.0.1:5000\n"
                "#EXTINF:-1,RTMP channel\nrtmp://fixture.example/live\n")
        result = audit_contents(source, [], lambda _: body)
        self.assertEqual(result["source_status_counts"], {
            "PARSED_WITH_NON_HTTP_REFERENCES_NOT_PLAYBACK_VERIFIED": 1})
        self.assertEqual(result["non_http_reference_count"], 2)
        self.assertEqual(result["unpaired_extinf_count"], 0)
        self.assertEqual(result["union_unique_url_sha256"], 1)

    def test_malformed_extinf_still_requires_review(self):
        source = [{"id": "tr", "url": "https://fixture.example/feed.m3u"}]
        body = ("#EXTM3U\n#EXTINF:-1,Valid\nhttps://fixture.example/one.m3u8\n"
                "#EXTINF:-1,No playable location\n")
        result = audit_contents(source, [], lambda _: body)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["source_results"][0]["unpaired_extinf"], 1)

    def test_headerless_original_source_normalized_only_when_proven_historical(self):
        src = [{"id": "github-auto-8", "url": "https://fixture.example/old.m3u",
                "historical_source_only": True}]
        content = "#EXTINF:-1,Original listing\nhttps://fixture.example/old.m3u8\n"
        report = audit_contents(src, [digest("https://fixture.example/old.m3u8")],
                                lambda _: content)
        self.assertEqual(report["source_status_counts"],
                         {"PARSED_HISTORICAL_HEADERLESS_NORMALIZED_NO_PLAYBACK": 1})
        self.assertEqual(report["historical_identifiers_present_in_current_sources"], 1)
        self.assertTrue(report["source_results"][0]["historical_header_normalized"])
        generic = [{"id": "generic", "url": src[0]["url"]}]
        rejected = audit_contents(generic, [], lambda _: content)
        self.assertEqual(rejected["source_status_counts"],
                         {"SOURCE_CONTENT_FAILED": 1})

    def test_documented_no_public_stream_is_not_misreported_as_broken(self):
        source = [{"id": "free-tv", "url": "https://fixture.example/free.m3u"}]
        body = ("#EXTM3U\n#EXTINF:-1,No public stream\n[NO PUBLIC STREAM]\n"
                "#EXTINF:-1,Valid\nhttps://fixture.example/valid.m3u8\n")
        result = audit_contents(source, [], lambda _: body)
        self.assertEqual(result["status"], "COMPLETE_SOURCE_CONTENT_PARSED")
        self.assertEqual(result["unpaired_extinf_count"], 1)
        self.assertEqual(result["actual_malformed_extinf_count"], 0)
        self.assertEqual(result["source_status_counts"],
                         {"PARSED_WITH_DECLARED_NO_PUBLIC_STREAM_PLACEHOLDERS": 1})

    def test_upstream_placeholder_and_adjacent_extinf_not_mislabeled_as_streams(self):
        source = [{"id": "tr", "url": "https://fixture.example/tr.m3u"}]
        body = ("#EXTM3U\n#EXTINF:-1,No public stream\n"
                "[NO PUBLIC STREAM]\n"
                "#EXTINF:-1,No location\n"
                "#EXTINF:-1,Real\nhttps://fixture.example/valid.m3u8\n")
        result = audit_contents(source, [], lambda _: body)
        self.assertEqual(result["unpaired_extinf_count"], 2)
        self.assertEqual(result["unpaired_reason_totals"],
                         {"EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER": 1,
                          "MISSING_URI_BEFORE_NEXT_EXTINF": 1})
        self.assertEqual(result["union_unique_url_sha256"], 1)

    def test_failed_one_does_not_erase_other_or_leak_token(self):
        sources = [{"id": "one", "url": "https://fixture.example/a?token=SECRET"},
                   {"id": "two", "url": "https://fixture.example/b"}]
        def fetch(url):
            if "SECRET" in url:
                raise RuntimeError("SECRET_PRIVATE_QUERY")
            return "#EXTM3U\n#EXTINF:-1,Good\nhttps://fixture.example/good.m3u8\n"
        r = audit_contents(sources, [], fetch)
        self.assertEqual(r["source_content_review_required"], 1)
        self.assertEqual(r["union_unique_url_sha256"], 1)
        self.assertNotIn("SECRET", str(r))

    def test_duplicate_urls_counted_once_but_raw_entries_retained(self):
        source = [{"id": "tr", "url": "https://fixture.example/tr.m3u"}]
        body = "#EXTM3U\n" + ("#EXTINF:-1,Chan\nhttps://fixture.example/a.m3u8\n" * 2)
        result = audit_contents(source, [digest("https://fixture.example/a.m3u8")],
                                lambda _: body)
        self.assertEqual(result["source_results"][0]["entries"], 2)
        self.assertEqual(result["source_results"][0]["unique_urls"], 1)
        self.assertEqual(result["source_results"][0]["duplicate_url_entries"], 1)

    def test_corrupt_or_duplicate_historical_sha_fails_closed(self):
        source = [{"id": "tr", "url": "https://fixture.example/tr.m3u"}]
        for baseline in ([digest("a"), digest("a")], ["not-a-sha"]):
            with self.subTest(baseline=baseline), self.assertRaises(ValueError):
                audit_contents(source, baseline, lambda _: "#EXTM3U\n")


if __name__ == "__main__":
    unittest.main()
