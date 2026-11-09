#!/usr/bin/env python3
"""Grouped no-network 309 stream-less IDs and 344 EPG-gap safety regressions."""
import copy
import hashlib
import unittest
from traz_gap_crosswalk import reconcile,inspect_xmltv,inspect_epg_gap

import urllib.request
from unittest.mock import patch
from traz_gap_crosswalk import SameHostRedirect

def digest(x):return hashlib.sha256(x.encode()).hexdigest()

def fixtures():
    a,b,c=(digest(x) for x in ("a","b","c"))
    api={"schema":1,"kind":"TR_AZ_WORLDWIDE_IPTV_API_SOURCE_LEADS",
       "policy":"READ_ONLY_METADATA_NOT_AV_NO_IBO_WRITES",
       "all_streams_av_verified":False,"protected_playlist_modified":False,
       "target_unique_channel_ids":4,"target_identities_without_epg_reference":3,
       "identities_without_stream_url_lead":["Alpha.tr","Beta.az","Gamma.tr"],
       "identities_missing_epg":["Alpha.tr","Beta.az","Gamma.tr"],
       "unique_channel_url_pairs":1,
       "stream_references":[{"channel_id":"Other.tr","url_sha256":c,"av_verified":False}]}
    scan={"schema":1,"playback_verified":False,"candidate_status":"UNVERIFIED",
       "coverage_status":"PARTIAL_SOURCE_FETCH","source_fetch_complete":False,
       "total_unique_candidates":3,
       "candidates":[
        {"url_sha256":a,"tvg_id":"Alpha.tr","source_ids":["iptv-org-tr"]},
        {"url_sha256":b,"tvg_id":"Beta.az","source_ids":["source-az"]},
        {"url_sha256":c,"tvg_id":"Gamma.tr","source_ids":["source-multi"]}]}
    return api,scan

class GapCrosswalkTests(unittest.TestCase):
    def test_exact_missing_id_and_hash_only_not_av(self):
        api,scan=fixtures()
        r=reconcile(api,scan)
        self.assertEqual(r["missing_api_stream_identities"],3)
        self.assertEqual(r["exact_missing_stream_identities_with_other_m3u_leads"],2)
        self.assertEqual(r["identity_collisions_for_manual_review"][0]["channel_id"],"Gamma.tr")
        self.assertEqual(r["still_without_exact_source_metadata"],1)
        self.assertFalse(r["source_scan_complete"])
        self.assertEqual(r["new_video_audio_verified"],0)
        self.assertNotIn("https://",str(r))
        self.assertFalse(r["ibo_device_verified"])

    def test_alias_or_similar_name_cannot_become_identity_match(self):
        api,scan=fixtures()
        scan["candidates"][0]["tvg_id"]="Alpha Television.tr"
        r=reconcile(api,scan)
        self.assertEqual(r["exact_missing_stream_identities_with_other_m3u_leads"],1)

    def test_fake_playback_and_plaintext_source_rejected(self):
        for mode in ("api_av","m3u_av","plaintext","duplicate","count"):
            api,scan=fixtures()
            if mode=="api_av":api["all_streams_av_verified"]=True
            if mode=="m3u_av":scan["playback_verified"]=True
            if mode=="plaintext":scan["candidates"][0]["url"]="https://example.org/a.m3u8"
            if mode=="duplicate":scan["candidates"][1]["url_sha256"]=scan["candidates"][0]["url_sha256"]
            if mode=="count":api["target_identities_without_epg_reference"]=1
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                reconcile(api,scan)

    def test_m3u_provenance_is_never_silently_truncated(self):
        api,scan=fixtures()
        scan["candidates"][0]["source_ids"]=["source-"+str(i) for i in range(13)]
        with self.assertRaisesRegex(ValueError,"Too many M3U source provenance identities"):
            reconcile(api,scan)
        scan["candidates"][0]["source_ids"]=["iptv-org-tr"]*13
        report=reconcile(api,scan)
        candidate=next(x for x in report["candidate_identities"] if x["channel_id"]=="Alpha.tr")
        self.assertEqual(candidate["candidate_m3u_url_hashes"][0]["source_ids"],["iptv-org-tr"])

    def test_invalid_m3u_provenance_fails_closed(self):
        for bad in (None,"iptv-org-tr",["https://example.org/source"],
                    ["source"+chr(10)+"injected"],["x"*97],["ok"]*101):
            api,scan=fixtures()
            scan["candidates"][0]["source_ids"]=bad
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"Invalid M3U source provenance"):
                reconcile(api,scan)
        api,scan=fixtures()
        scan["candidates"][0]["source_ids"]=[]
        self.assertEqual(reconcile(api,scan)["exact_missing_stream_identities_with_other_m3u_leads"],2)

    def test_malformed_api_source_identity_rejected(self):
        for bad in ("", "https://example.org/live", "Alpha.tr"+chr(10)+"Injected", "x"*201):
            api,scan=fixtures()
            api["stream_references"][0]["channel_id"]=bad
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"Invalid API hash-only identity"):
                reconcile(api,scan)

    def test_duplicate_api_channel_hash_pair_is_rejected(self):
        api,scan=fixtures()
        api["stream_references"].append(copy.deepcopy(api["stream_references"][0]))
        api["unique_channel_url_pairs"]=2
        with self.assertRaisesRegex(ValueError,"Duplicate API channel and URL hash pair"):
            reconcile(api,scan)
        api["stream_references"][1]["channel_id"]="Different.tr"
        result=reconcile(api,scan)
        self.assertEqual(result["exact_missing_stream_identities_with_other_m3u_leads"],2)

    def test_exact_xmltv_channel_and_programme_not_schedule_accuracy(self):
        xml=b'<tv><channel id="Alpha.tr"/><channel id="Other.tr"/><programme channel="Alpha.tr" start="20261105080000 +0000" stop="20261105090000 +0000"><title>News</title></programme></tv>'
        ids,programme=inspect_xmltv(xml,{"Alpha.tr","Beta.az"})
        self.assertEqual(ids,{"Alpha.tr"})
        self.assertEqual(programme["Alpha.tr"],1)
        report=inspect_epg_gap(["Alpha.tr","Beta.az"],["https://example.org/epg.xml"],
                 fetcher=lambda _:xml)
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],1)
        self.assertEqual(report["exact_xmltv_ids_with_programme_records"],1)
        self.assertEqual(report["remaining_without_xmltv_channel_id_candidate"],1)
        self.assertFalse(report["schedules_correctly_verified"])

    def test_cross_source_exact_xmltv_id_collision_is_flagged_not_verified(self):
        xml=b'<tv><channel id="Alpha.tr"/><programme channel="Alpha.tr"/></tv>'
        report=inspect_epg_gap(["Alpha.tr","Beta.az"],
            ["https://example.org/first.xml","https://example.org/second.xml"],
            fetcher=lambda _:xml)
        self.assertEqual(report["cross_source_xmltv_id_collisions"],["Alpha.tr"])
        self.assertEqual(report["cross_source_xmltv_collision_count"],1)
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],1)
        self.assertTrue(report["cross_source_collision_requires_manual_review"])
        self.assertFalse(report["schedules_correctly_verified"])
        single=inspect_epg_gap(["Alpha.tr"],["https://example.org/first.xml"],fetcher=lambda _:xml)
        self.assertEqual(single["cross_source_xmltv_id_collisions"],[])
        self.assertFalse(single["cross_source_collision_requires_manual_review"])
        empty=inspect_epg_gap(["Alpha.tr"],[],fetcher=lambda _:xml)
        self.assertFalse(empty["cross_source_collision_requires_manual_review"])

    def test_duplicate_xmltv_source_url_is_not_cross_source_collision(self):
        xml=b'<tv><channel id="Alpha.tr"/></tv>'
        report=inspect_epg_gap(["Alpha.tr"],
            ["https://example.org/guide.xml","https://example.org/guide.xml"],
            fetcher=lambda _:xml)
        self.assertEqual(report["parsed_sources"],1)
        self.assertTrue(report["all_sources_parsed"])
        self.assertEqual(report["cross_source_xmltv_id_collisions"],[])
        self.assertFalse(report["cross_source_collision_requires_manual_review"])
        self.assertEqual(report["source_results"][1]["status"],"XMLTV_DUPLICATE_SOURCE_SKIPPED")

    def test_repeated_xmltv_url_retries_after_first_parse_failure(self):
        xml=b'<tv><channel id="Alpha.tr"/></tv>'
        attempts=[]
        def flaky(url):
            attempts.append(url)
            return b"<tv>" if len(attempts)==1 else xml
        report=inspect_epg_gap(["Alpha.tr"],
            ["https://example.org/guide.xml","https://example.org/guide.xml"],fetcher=flaky)
        self.assertEqual(len(attempts),2)
        self.assertEqual(report["parsed_sources"],1)
        self.assertFalse(report["all_sources_parsed"])
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],1)
        self.assertEqual(report["source_results"][0]["status"],"XMLTV_UNVERIFIED_ValueError")
        self.assertEqual(report["source_results"][1]["status"],"XMLTV_PARSED")
        self.assertFalse(report["cross_source_collision_requires_manual_review"])

    def test_xmltv_programme_without_declared_channel_is_not_evidence(self):
        raw=b'<tv><programme channel="Alpha.tr"/><channel id="Beta.az"/></tv>'
        channels,programmes=inspect_xmltv(raw,{"Alpha.tr","Beta.az"})
        self.assertEqual(channels,{"Beta.az"})
        self.assertEqual(programmes, {})
        report=inspect_epg_gap(["Alpha.tr","Beta.az"],["https://example.org/guide.xml"],fetcher=lambda _:raw)
        self.assertEqual(report["exact_xmltv_ids_with_programme_records"],0)
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],1)
        ordered=b'<tv><programme channel="Alpha.tr"/><channel id="Alpha.tr"/></tv>'
        channels,programmes=inspect_xmltv(ordered,{"Alpha.tr"})
        self.assertEqual(programmes["Alpha.tr"],1)

    def test_unrequested_xmltv_channel_duplicate_fails_closed(self):
        raw=b'<tv><channel id="Other.tr"/><channel id="Other.tr"/><channel id="Alpha.tr"/></tv>'
        with self.assertRaisesRegex(ValueError,"Duplicate XMLTV channel identity"):
            inspect_xmltv(raw,{"Alpha.tr"})
        report=inspect_epg_gap(["Alpha.tr"],["https://example.org/guide.xml"],fetcher=lambda _:raw)
        self.assertEqual(report["parsed_sources"],0)
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],0)

    def test_malformed_unrequested_xmltv_channel_identity_fails_closed(self):
        for raw in (b'<tv><channel/></tv>',b'<tv><channel id=""/></tv>',
                    b'<tv><channel id="Other&#10;tr"/></tv>'):
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,"Malformed XMLTV channel identity"):
                inspect_xmltv(raw,{"Alpha.tr"})

    def test_duplicate_channel_id_inside_single_xmltv_source_is_rejected(self):
        duplicated=b'<tv><channel id="Alpha.tr"/><channel id="Alpha.tr"/></tv>'
        with self.assertRaisesRegex(ValueError,"Duplicate XMLTV channel identity"):
            inspect_xmltv(duplicated,{"Alpha.tr"})
        report=inspect_epg_gap(["Alpha.tr"],["https://example.org/epg.xml"],
            fetcher=lambda _:duplicated)
        self.assertEqual(report["parsed_sources"],0)
        self.assertEqual(report["exact_xmltv_channel_id_candidates"],0)
        self.assertFalse(report["all_sources_parsed"])

    def test_bad_xmltv_and_source_failure_fail_partial_without_fake_epg(self):
        for raw in (b"<html></html>",b"<tv>",b"<!DOCTYPE foo><not-tv/>"):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                inspect_xmltv(raw,{"Alpha.tr"})
        def bad(url): raise OSError("offline")
        r=inspect_epg_gap(["Alpha.tr"],["https://x.example.org/epg.xml"],fetcher=bad)
        self.assertEqual(r["parsed_sources"],0)
        self.assertFalse(r["all_sources_parsed"])
        self.assertEqual(r["exact_xmltv_channel_id_candidates"],0)

    def test_iptv_org_feed_variant_is_same_exact_broadcaster_only_if_source_trusted(self):
        from traz_gap_crosswalk import canonical_tvg_id
        self.assertEqual(canonical_tvg_id("Alpha.tr@SD",["iptv-org-tr-streams"]),"alpha.tr")
        self.assertEqual(canonical_tvg_id("Alpha.tr@HD",["iptv-org-tr"]),"alpha.tr")
        self.assertEqual(canonical_tvg_id("Alpha.tr@SD",["untrusted"]), "alpha.tr@sd")
        self.assertEqual(canonical_tvg_id("Alpha.tr@HD",["iptv-org.evil"]), "alpha.tr@hd")
        self.assertEqual(canonical_tvg_id("Alpha.tr@HD",["iptv-org:spoof"]), "alpha.tr@hd")
        self.assertEqual(canonical_tvg_id("Alpha.tr@weird",["iptv-org-tr"]),"alpha.tr@weird")
        api,scan=fixtures()
        scan["candidates"][0]["tvg_id"]="Alpha.tr@SD"
        scan["candidates"][0]["source_ids"]=["iptv-org-tr-streams"]
        report=reconcile(api,scan)
        self.assertEqual(report["exact_missing_stream_identities_with_other_m3u_leads"],2)
        api,scan=fixtures()
        scan["candidates"][0]["tvg_id"]="Alpha.tr@SD"
        scan["candidates"][0]["source_ids"]=["untrusted"]
        report=reconcile(api,scan)
        self.assertEqual(report["exact_missing_stream_identities_with_other_m3u_leads"],1)

if __name__=="__main__":
    unittest.main()

class XMLTVRedirectSafetyTests(unittest.TestCase):
    def test_redirect_rejects_same_host_unsafe_target(self):
        req=urllib.request.Request("https://example.org/guide.xml")
        handler=SameHostRedirect()
        for target in ("https://example.org:8443/private",
                       "https://user:pass@example.org/guide.xml",
                       "https://example.org/guide.xml#fragment",
                       "http://example.org/guide.xml",
                       "https://different.example.org/guide.xml"):
            with self.subTest(target=target),patch("traz_gap_crosswalk._source_check",return_value=False),self.assertRaises(ValueError):
                handler.redirect_request(req,None,302,"Found",{},target)

