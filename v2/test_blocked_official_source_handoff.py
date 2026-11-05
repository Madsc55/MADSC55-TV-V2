#!/usr/bin/env python3
"""Grouped no-network exact-source handoff regression for blocked TV websites."""
import hashlib
import json
import unittest
from blocked_official_source_handoff import SOURCES, TARGETS, audit, exact_target


def config():
    return {"sources": [{"id":sid, "url":"https://example.org/"+sid+".m3u"}
                        for sid in sorted(SOURCES)]}


def feed(*pairs):
    return "#EXTM3U\n" + "".join(meta+"\n"+url+"\n" for meta,url in pairs)


class BlockedOfficialHandoffTests(unittest.TestCase):
    def test_exact_tvg_id_and_name_only(self):
        self.assertEqual(exact_target({"tvg_id":"TV100.tr@SD","name":"TV 100 (1080p)"}),
                         "tv100-official")
        self.assertEqual(exact_target({"tvg_id":"BenguturkTV.tr@SD",
                                       "name":"BENGÜTÜRK TV (720p) [Not 24/7]"}),
                         "benguturk-official")
        for pair in ({"tvg_id":"TV100.tr@SD","name":"TV 101"},
                     {"tvg_id":"","name":"TV 100"},
                     {"tvg_id":"HalkTV.tr@SD","name":"Halk TV Copy"},
                     {"tvg_id":"UlusalKanal.tr@SD","name":"Ülke TV"}):
            self.assertIsNone(exact_target(pair))

    def test_two_sources_reconcile_same_url_without_fake_av(self):
        one = '#EXTINF:-1 tvg-id="TV100.tr@SD",TV 100 (1080p)'
        two = '#EXTINF:-1 tvg-id="HalkTV.tr@SD",Halk TV'
        url = "https://example.org/tv100.m3u8?app=web"
        docs = {sid:feed() for sid in SOURCES}
        docs["iptv-org-tr"] = feed((one,url),(two,"https://example.org/halk.m3u8"))
        docs["iptv-turk-tr"] = feed((one,url))
        result, rows = audit(config(),reader=lambda source:
                             docs[source.rsplit("/",1)[-1].removesuffix(".m3u")])
        self.assertEqual(result["configured_sources_valid"],6)
        self.assertEqual(result["candidate_url_count"],2)
        self.assertEqual(result["candidate_channel_counts"]["tv100-official"],1)
        selected = next(x for x in rows if x["url"] == url)
        self.assertEqual(selected["source_ids"],["iptv-org-tr","iptv-turk-tr"])
        self.assertEqual(selected["matched_blocked_pages"],["tv100-official"])
        self.assertEqual(selected["url_sha256"],hashlib.sha256(url.encode()).hexdigest())
        self.assertNotIn(url,json.dumps(result))
        self.assertFalse(result["video_audio_verified"])
        self.assertFalse(result["remaining_official_http_access_errors_resolved"])

    def test_partial_external_errors_not_disguised(self):
        one = '#EXTINF:-1 tvg-id="TRTSpor.tr@SD",TRT Spor (720p)'
        result, rows = audit(config(),reader=lambda url:
                             (_ for _ in ()).throw(OSError("unavailable"))
                             if url.endswith("iptv-turk-tr.m3u") else
                             feed((one,"https://example.org/trt.m3u8")))
        self.assertEqual(result["configured_sources_valid"],5)
        self.assertEqual(result["candidate_channel_counts"]["trt-spor-official"],1)
        self.assertEqual(result["source_status"]["iptv-turk-tr"],"UNAVAILABLE_OR_INVALID")
        self.assertEqual(len(rows),1)
        self.assertFalse(result["external_source_coverage_complete"])

    def test_ulusal_kanal_exact_approved_sixth_source_only(self):
        line = '#EXTINF:-1 tvg-id="UlusalKanal.tr",Ulusal Kanal (720p)'
        docs = {sid: feed() for sid in SOURCES}
        docs["sayatsirinoglu-tr"] = feed(
            (line, "https://stream.example.org/ulusaltv/index.m3u8"))
        report, rows = audit(config(), reader=lambda uri:
                             docs[uri.rsplit("/", 1)[-1].removesuffix(".m3u")])
        self.assertEqual(report["configured_sources_checked"], 6)
        self.assertEqual(report["candidate_channel_counts"]["ulusal-kanal-official"], 1)
        self.assertEqual(report["blocked_page_ids_without_exact_candidate"],
                         ["trt-spor-official", "tv100-official",
                          "benguturk-official", "halk-tv-official"])
        self.assertEqual(rows[0]["source_ids"], ["sayatsirinoglu-tr"])
        self.assertFalse(report["video_audio_verified"])

    def test_private_invalid_url_rejected_and_no_name_only_matching(self):
        pair = '#EXTINF:-1 tvg-id="TV100.tr",TV 100'
        result, rows = audit(config(),reader=lambda url: feed(
            (pair,"http://127.0.0.1/internal.m3u8"),
            ('#EXTINF:-1,TV 100',"https://example.org/not-exact.m3u8")))
        self.assertEqual(rows,[])
        self.assertEqual(result["blocked_page_count_with_candidate"],0)

    def test_missing_or_untrusted_source_inventory_fails_closed(self):
        rows = config()
        rows["sources"][0]["url"]="http://127.0.0.1/private.m3u"
        with self.assertRaises(ValueError):
            audit(rows,reader=lambda _: self.fail("No fetch on invalid source"))
        self.assertEqual(len(TARGETS),5)


if __name__ == "__main__":
    unittest.main()
