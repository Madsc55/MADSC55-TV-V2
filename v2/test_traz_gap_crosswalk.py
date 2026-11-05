#!/usr/bin/env python3
"""Grouped no-network 309 stream-less IDs and 344 EPG-gap safety regressions."""
import copy
import hashlib
import unittest
from traz_gap_crosswalk import reconcile,inspect_xmltv,inspect_epg_gap

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

    def test_bad_xmltv_and_source_failure_fail_partial_without_fake_epg(self):
        for raw in (b"<html></html>",b"<tv>",b"<!DOCTYPE foo><not-tv/>"):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                inspect_xmltv(raw,{"Alpha.tr"})
        def bad(url): raise OSError("offline")
        r=inspect_epg_gap(["Alpha.tr"],["https://x.example.org/epg.xml"],fetcher=bad)
        self.assertEqual(r["parsed_sources"],0)
        self.assertFalse(r["all_sources_parsed"])
        self.assertEqual(r["exact_xmltv_channel_id_candidates"],0)

if __name__=="__main__":
    unittest.main()
